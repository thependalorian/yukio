"""
Database utilities using LanceDB for local vector storage.

This module provides a zero-config local vector database for Yukio,
replacing PostgreSQL/pgvector with LanceDB for simpler local deployment.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pyarrow as pa

import lancedb
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LanceDBManager:
    """Manages LanceDB connection and operations."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize LanceDB manager.

        Args:
            db_path: Path to LanceDB database directory
        """
        self.db_path = db_path or os.getenv("LANCEDB_PATH", "./yukio_data/lancedb")
        self.table_name = os.getenv("LANCEDB_TABLE_NAME", "japanese_lessons")
        self.db: Optional[lancedb.DBConnection] = None
        self._initialized = False

    def initialize(self):
        """Initialize LanceDB connection."""
        if self._initialized:
            return

        # Ensure directory exists
        os.makedirs(self.db_path, exist_ok=True)

        # Connect to LanceDB
        self.db = lancedb.connect(self.db_path)
        self._initialized = True
        logger.info(f"LanceDB initialized at {self.db_path}")

    def close(self):
        """Close LanceDB connection."""
        self.db = None
        self._initialized = False
        logger.info("LanceDB connection closed")

    def _ensure_initialized(self):
        """Ensure database is initialized."""
        if not self._initialized:
            self.initialize()

    def create_table(self, embedding_dim: int = 768):
        """
        Create the main chunks table if it doesn't exist.

        Args:
            embedding_dim: Dimension of embedding vectors (default 768 for nomic-embed-text)
        """
        self._ensure_initialized()

        if self.table_name in self.db.list_tables():
            logger.info(f"Table {self.table_name} already exists")
            return

        # Define schema using PyArrow
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("document_id", pa.string()),
            pa.field("document_title", pa.string()),
            pa.field("document_source", pa.string()),
            pa.field("content", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("metadata", pa.string()),  # JSON string
            pa.field("vector", pa.list_(pa.float32(), embedding_dim)),
            pa.field("created_at", pa.string()),
        ])

        # Create empty table with schema
        self.db.create_table(self.table_name, schema=schema)
        logger.info(f"Created table {self.table_name} with embedding dimension {embedding_dim}")

    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        document_id: str,
        document_title: str,
        document_source: str
    ) -> int:
        """
        Add document chunks to the database.

        Args:
            chunks: List of chunks with 'content', 'embedding', and 'metadata'
            document_id: Document ID
            document_title: Document title
            document_source: Document source

        Returns:
            Number of chunks added
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            # Determine embedding dimension from first chunk
            if chunks and "embedding" in chunks[0]:
                embedding_dim = len(chunks[0]["embedding"])
            else:
                embedding_dim = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
            self.create_table(embedding_dim)

        # Prepare data for insertion
        data = []
        for i, chunk in enumerate(chunks):
            data.append({
                "id": str(uuid4()),
                "document_id": document_id,
                "document_title": document_title,
                "document_source": document_source,
                "content": chunk["content"],
                "chunk_index": chunk.get("chunk_index", i),
                "metadata": json.dumps(chunk.get("metadata", {})),
                "vector": chunk["embedding"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # Add to table
        table = self.db.open_table(self.table_name)
        table.add(data)

        logger.info(f"Added {len(data)} chunks for document {document_title}")
        return len(data)

    def vector_search(
        self,
        embedding: List[float],
        limit: int = 10,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            filter_expr: Optional SQL-like filter expression

        Returns:
            List of matching chunks ordered by similarity (best first)
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            logger.warning(f"Table {self.table_name} does not exist")
            return []

        table = self.db.open_table(self.table_name)

        # Build search query
        query = table.search(embedding).limit(limit)

        if filter_expr:
            query = query.where(filter_expr)

        results = query.to_list()

        # Convert to standard format
        return [
            {
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "content": r["content"],
                "similarity": 1.0 - r["_distance"],  # Convert distance to similarity
                "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                "document_title": r["document_title"],
                "document_source": r["document_source"],
            }
            for r in results
        ]

    def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + full-text).

        LanceDB supports full-text search natively. This combines
        vector similarity with text matching.

        Args:
            embedding: Query embedding vector
            query_text: Query text for full-text search
            limit: Maximum number of results
            text_weight: Weight for text similarity (0-1)

        Returns:
            List of matching chunks ordered by combined score
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            logger.warning(f"Table {self.table_name} does not exist")
            return []

        table = self.db.open_table(self.table_name)

        # LanceDB hybrid search
        try:
            # Try hybrid search - LanceDB API may vary by version
            # First try with columns parameter
            try:
                results = (
                    table.search(embedding, query_type="hybrid")
                    .text(query_text, columns=["content"])
                    .limit(limit)
                    .to_list()
                )
            except TypeError:
                # Fallback: try without columns parameter
                results = (
                    table.search(embedding, query_type="hybrid")
                    .text(query_text)
                    .limit(limit)
                    .to_list()
                )
        except Exception as e:
            # Fall back to vector-only search if hybrid not available
            logger.warning(f"Hybrid search failed, falling back to vector: {e}")
            return self.vector_search(embedding, limit)

        return [
            {
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "content": r["content"],
                "combined_score": 1.0 - r.get("_distance", 0),
                "vector_similarity": 1.0 - r.get("_distance", 0),
                "text_similarity": r.get("_relevance_score", 0),
                "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
                "document_title": r["document_title"],
                "document_source": r["document_source"],
            }
            for r in results
        ]

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            List of chunks ordered by chunk index
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            return []

        table = self.db.open_table(self.table_name)

        results = (
            table.search()
            .where(f"document_id = '{document_id}'")
            .to_list()
        )

        # Sort by chunk index
        results.sort(key=lambda x: x.get("chunk_index", 0))

        return [
            {
                "chunk_id": r["id"],
                "content": r["content"],
                "chunk_index": r["chunk_index"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
            }
            for r in results
        ]

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List unique documents in the database.

        Args:
            limit: Maximum number of documents
            offset: Number of documents to skip

        Returns:
            List of document metadata
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            return []

        table = self.db.open_table(self.table_name)

        # Get all records and extract unique documents
        df = table.to_pandas()

        if df.empty:
            return []

        # Group by document_id to get unique documents with counts
        documents = {}
        for _, row in df.iterrows():
            doc_id = row["document_id"]
            if doc_id not in documents:
                documents[doc_id] = {
                    "id": doc_id,
                    "title": row["document_title"],
                    "source": row["document_source"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "created_at": row["created_at"],
                    "updated_at": row["created_at"],
                    "chunk_count": 0,
                }
            documents[doc_id]["chunk_count"] += 1

        # Convert to list and apply pagination
        doc_list = list(documents.values())
        doc_list.sort(key=lambda x: x["created_at"], reverse=True)

        return doc_list[offset:offset + limit]

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document data or None if not found
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            return None

        table = self.db.open_table(self.table_name)

        results = (
            table.search()
            .where(f"document_id = '{document_id}'")
            .limit(1)
            .to_list()
        )

        if not results:
            return None

        r = results[0]

        # Get all chunks to build full content
        chunks = self.get_document_chunks(document_id)
        full_content = "\n\n".join([c["content"] for c in chunks])

        return {
            "id": document_id,
            "title": r["document_title"],
            "source": r["document_source"],
            "content": full_content,
            "metadata": json.loads(r["metadata"]) if r["metadata"] else {},
            "created_at": r["created_at"],
            "updated_at": r["created_at"],
        }

    def delete_document(self, document_id: str) -> bool:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            True if deleted, False if not found
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            return False

        table = self.db.open_table(self.table_name)

        try:
            table.delete(f"document_id = '{document_id}'")
            logger.info(f"Deleted document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dictionary with database stats
        """
        self._ensure_initialized()

        if self.table_name not in self.db.list_tables():
            return {
                "total_chunks": 0,
                "total_documents": 0,
                "tables": [],
            }

        table = self.db.open_table(self.table_name)
        df = table.to_pandas()

        return {
            "total_chunks": len(df),
            "total_documents": df["document_id"].nunique() if not df.empty else 0,
            "tables": self.db.list_tables(),
            "db_path": self.db_path,
        }


# Global database manager instance
db_manager = LanceDBManager()


# Convenience functions for compatibility with existing code
async def initialize_database():
    """Initialize database connection."""
    db_manager.initialize()


async def close_database():
    """Close database connection."""
    db_manager.close()


async def vector_search(
    embedding: List[float],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Perform vector similarity search.

    Args:
        embedding: Query embedding vector
        limit: Maximum number of results

    Returns:
        List of matching chunks
    """
    return db_manager.vector_search(embedding, limit)


async def hybrid_search(
    embedding: List[float],
    query_text: str,
    limit: int = 10,
    text_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search.

    Args:
        embedding: Query embedding vector
        query_text: Query text for keyword search
        limit: Maximum number of results
        text_weight: Weight for text similarity

    Returns:
        List of matching chunks
    """
    return db_manager.hybrid_search(embedding, query_text, limit, text_weight)


async def get_document(document_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID."""
    return db_manager.get_document(document_id)


async def list_documents(
    limit: int = 100,
    offset: int = 0,
    metadata_filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """List documents with optional filtering."""
    return db_manager.list_documents(limit, offset)


async def get_document_chunks(document_id: str) -> List[Dict[str, Any]]:
    """Get all chunks for a document."""
    return db_manager.get_document_chunks(document_id)


async def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful
    """
    try:
        db_manager.initialize()
        stats = db_manager.get_stats()
        logger.info(f"Database connection successful. Stats: {stats}")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


# Session Management Functions (Simple in-memory implementation)
# For production, consider using Mem0 or a proper session store
_sessions: Dict[str, Dict[str, Any]] = {}
_session_messages: Dict[str, List[Dict[str, Any]]] = {}


async def create_session(
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timeout_minutes: int = 60
) -> str:
    """
    Create a new session.

    Args:
        user_id: Optional user identifier
        metadata: Optional session metadata
        timeout_minutes: Session timeout in minutes

    Returns:
        Session ID
    """
    session_id = str(uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
    
    _sessions[session_id] = {
        "id": session_id,
        "user_id": user_id,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat()
    }
    _session_messages[session_id] = []
    
    return session_id


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get session by ID.

    Args:
        session_id: Session ID

    Returns:
        Session data or None if not found/expired
    """
    if session_id not in _sessions:
        return None
    
    session = _sessions[session_id]
    expires_at = datetime.fromisoformat(session["expires_at"])
    
    if datetime.now(timezone.utc) > expires_at:
        # Session expired, remove it
        del _sessions[session_id]
        if session_id in _session_messages:
            del _session_messages[session_id]
        return None
    
    return session


async def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add a message to a session.

    Args:
        session_id: Session ID
        role: Message role (user, assistant)
        content: Message content
        metadata: Optional message metadata
    """
    if session_id not in _session_messages:
        _session_messages[session_id] = []
    
    _session_messages[session_id].append({
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


async def get_session_messages(
    session_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get messages for a session.

    Args:
        session_id: Session ID
        limit: Maximum number of messages to return

    Returns:
        List of messages
    """
    if session_id not in _session_messages:
        return []
    
    messages = _session_messages[session_id]
    return messages[-limit:] if limit > 0 else messages
