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
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in LanceDB."""
        try:
            # Try to open the table - if it doesn't exist, this will raise an exception
            self.db.open_table(table_name)
            return True
        except Exception:
            return False

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

        if self._table_exists(self.table_name):
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

    def create_user_progress_table(self):
        """
        Create a table for storing user progress, lessons, vocabulary, and XP.
        This is separate from the document chunks table.
        """
        self._ensure_initialized()
        table_name = "user_progress"

        if self._table_exists(table_name):
            logger.info(f"Table {table_name} already exists")
            return

        # Define schema for user progress
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("user_id", pa.string()),
            pa.field("type", pa.string()),  # 'lesson', 'vocab', 'quiz', 'xp', 'streak'
            pa.field("item_id", pa.string()),  # lesson_id, vocab_id, etc.
            pa.field("status", pa.string()),  # 'completed', 'in_progress', 'locked', 'mastered'
            pa.field("data", pa.string()),  # JSON string with type-specific data
            pa.field("xp_earned", pa.int32()),
            pa.field("crowns", pa.int32()),
            pa.field("created_at", pa.string()),
            pa.field("updated_at", pa.string()),
        ])

        self.db.create_table(table_name, schema=schema)
        logger.info(f"Created table {table_name} for user progress tracking")

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

        if not self._table_exists(self.table_name):
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
            filter_expr: Optional filter expression

        Returns:
            List of matching chunks
        """
        self._ensure_initialized()

        if not self._table_exists(self.table_name):
            logger.warning(f"Table {self.table_name} does not exist")
            return []

        table = self.db.open_table(self.table_name)

        # Perform vector search
        try:
            query = table.search(embedding).limit(limit)
            if filter_expr:
                query = query.where(filter_expr)
            results = query.to_list()
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

        # Parse metadata from JSON strings
        for result in results:
            if "metadata" in result and isinstance(result["metadata"], str):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except json.JSONDecodeError:
                    result["metadata"] = {}

        return results

    def hybrid_search(
        self,
        embedding: List[float],
        query_text: str,
        limit: int = 10,
        text_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + text).

        Args:
            embedding: Query embedding vector
            query_text: Query text for text search
            limit: Maximum number of results
            text_weight: Weight for text search (0-1)

        Returns:
            List of matching chunks
        """
        self._ensure_initialized()

        if not self._table_exists(self.table_name):
            logger.warning(f"Table {self.table_name} does not exist")
            return []

        table = self.db.open_table(self.table_name)

        try:
            # Try hybrid search with columns parameter
            query = table.search(embedding).limit(limit)
            # LanceDB's text() method may vary - try with columns first
            try:
                results = query.text(query_text, columns=["content"]).to_list()
            except TypeError:
                # Fallback to vector-only search if text() doesn't support columns
                logger.debug("Text search with columns not supported, using vector search only")
                results = query.to_list()
        except Exception as e:
            logger.warning(f"Hybrid search failed, falling back to vector: {e}")
            # Fallback to vector search
            results = table.search(embedding).limit(limit).to_list()

        # Parse metadata
        for result in results:
            if "metadata" in result and isinstance(result["metadata"], str):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except json.JSONDecodeError:
                    result["metadata"] = {}

        return results

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document ID

        Returns:
            List of chunks
        """
        self._ensure_initialized()

        if not self._table_exists(self.table_name):
            return []

        table = self.db.open_table(self.table_name)
        results = table.search().where(f"document_id = '{document_id}'").to_list()

        # Parse metadata
        for result in results:
            if "metadata" in result and isinstance(result["metadata"], str):
                try:
                    result["metadata"] = json.loads(result["metadata"])
                except json.JSONDecodeError:
                    result["metadata"] = {}

        return sorted(results, key=lambda x: x.get("chunk_index", 0))

    def list_documents(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all unique documents in the database.

        Args:
            limit: Maximum number of documents
            offset: Offset for pagination

        Returns:
            List of document summaries
        """
        self._ensure_initialized()

        if not self._table_exists(self.table_name):
            return []

        table = self.db.open_table(self.table_name)
        
        # Get all chunks and group by document
        all_results = table.search().limit(10000).to_list()  # Get a large batch
        
        # Group by document_id
        documents = {}
        for result in all_results:
            doc_id = result.get("document_id")
            if doc_id not in documents:
                documents[doc_id] = {
                    "id": doc_id,
                    "title": result.get("document_title", "Unknown"),
                    "source": result.get("document_source", "Unknown"),
                    "chunk_count": 0,
                    "created_at": result.get("created_at", "")
                }
            documents[doc_id]["chunk_count"] += 1

        # Convert to list and paginate
        doc_list = list(documents.values())
        return doc_list[offset:offset + limit]

    # User Progress Methods
    def record_user_progress(
        self,
        user_id: str,
        progress_type: str,
        item_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
        xp_earned: int = 0,
        crowns: int = 0
    ) -> str:
        """
        Record user progress for lessons, vocabulary, quizzes, etc.

        Args:
            user_id: User identifier
            progress_type: Type of progress ('lesson', 'vocab', 'quiz', 'xp', 'streak')
            item_id: ID of the item (lesson_id, vocab_id, etc.)
            status: Status ('completed', 'in_progress', 'locked', 'mastered')
            data: Additional type-specific data
            xp_earned: XP earned from this action
            crowns: Crowns earned (for lessons)

        Returns:
            Progress record ID
        """
        self._ensure_initialized()
        self.create_user_progress_table()

        progress_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        table = self.db.open_table("user_progress")
        
        # Check if record exists
        existing = table.search().where(
            f"user_id = '{user_id}' AND type = '{progress_type}' AND item_id = '{item_id}'"
        ).to_list()

        if existing:
            # Update existing record
            record_id = existing[0].get("id")
            table.update({
                "status": status,
                "data": json.dumps(data or {}),
                "xp_earned": xp_earned,
                "crowns": crowns,
                "updated_at": now
            }).where(f"id = '{record_id}'").execute()
            return record_id
        else:
            # Create new record
            table.add([{
                "id": progress_id,
                "user_id": user_id,
                "type": progress_type,
                "item_id": item_id,
                "status": status,
                "data": json.dumps(data or {}),
                "xp_earned": xp_earned,
                "crowns": crowns,
                "created_at": now,
                "updated_at": now,
            }])
            return progress_id

    def get_user_progress(
        self,
        user_id: str,
        progress_type: Optional[str] = None,
        item_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get user progress records.

        Args:
            user_id: User identifier
            progress_type: Optional filter by type
            item_id: Optional filter by item_id

        Returns:
            List of progress records
        """
        self._ensure_initialized()
        
        if not self._table_exists("user_progress"):
            return []

        table = self.db.open_table("user_progress")
        
        query = table.search().where(f"user_id = '{user_id}'")
        
        if progress_type:
            # Note: LanceDB where() may need to be chained differently
            # This is a simplified approach
            results = query.to_list()
            results = [r for r in results if r.get("type") == progress_type]
        else:
            results = query.to_list()

        if item_id:
            results = [r for r in results if r.get("item_id") == item_id]

        # Parse data JSON
        for result in results:
            if "data" in result and isinstance(result["data"], str):
                try:
                    result["data"] = json.loads(result["data"])
                except json.JSONDecodeError:
                    result["data"] = {}

        return results

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get aggregated user statistics (XP, level, streak, etc.).

        Args:
            user_id: User identifier

        Returns:
            Dictionary with user stats
        """
        progress_records = self.get_user_progress(user_id)
        
        total_xp = sum(r.get("xp_earned", 0) for r in progress_records)
        lessons_completed = len([r for r in progress_records if r.get("type") == "lesson" and r.get("status") == "completed"])
        vocab_mastered = len([r for r in progress_records if r.get("type") == "vocab" and r.get("status") == "mastered"])
        
        # Calculate level (simple: 100 XP per level)
        level = max(1, (total_xp // 100) + 1)
        xp_to_next_level = 100 - (total_xp % 100)
        
        # Get streak from streak records
        streak_records = [r for r in progress_records if r.get("type") == "streak"]
        current_streak = 0
        if streak_records:
            latest_streak = max(streak_records, key=lambda x: x.get("updated_at", ""))
            current_streak = latest_streak.get("data", {}).get("days", 0) if isinstance(latest_streak.get("data"), dict) else 0

        # Get user name from user_id (simple mapping for now)
        # In production, this could come from a user profile table
        user_names = {
            "george_nekwaya": "George Nekwaya",
            "default_user": "Student"
        }
        name = user_names.get(user_id, user_id.replace("_", " ").title())
        
        # Check if user is a complete beginner (no lessons or vocab completed)
        is_beginner = lessons_completed == 0 and vocab_mastered == 0 and total_xp < 50
        
        # Set appropriate JLPT level based on progress
        # Complete beginner = N5 (starting point)
        if is_beginner:
            jlpt_level = "N5"
            daily_goal = 15  # Lower goal for beginners
        elif total_xp < 500:
            jlpt_level = "N5"
            daily_goal = 20
        elif total_xp < 2000:
            jlpt_level = "N4"
            daily_goal = 25
        elif total_xp < 5000:
            jlpt_level = "N3"
            daily_goal = 30
        else:
            jlpt_level = "N2"  # Advanced
            daily_goal = 35
        
        return {
            "user_id": user_id,
            "name": name,
            "level": level,
            "xp": total_xp,
            "xp_to_next_level": xp_to_next_level,
            "streak": current_streak,
            "lessons_completed": lessons_completed,
            "vocab_mastered": vocab_mastered,
            "daily_goal": daily_goal,
            "hearts": 3,  # Default
            "jlpt_level": jlpt_level,
        }


# Global database manager instance
db_manager = LanceDBManager()


# Database initialization functions
async def initialize_database():
    """Initialize the database connection."""
    db_manager.initialize()
    db_manager.create_table()
    db_manager.create_user_progress_table()


async def close_database():
    """Close the database connection."""
    db_manager.close()


async def test_connection() -> bool:
    """Test database connection."""
    try:
        db_manager._ensure_initialized()
        return db_manager.db is not None
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


# Session Management Functions
async def create_session(
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    timeout_minutes: int = 60
) -> str:
    """
    Create a new session.
    """
    session_id = str(uuid4())
    # In LanceDB, we don't have a dedicated 'sessions' table like in PostgreSQL.
    # We can store session metadata as a special document or in a separate table if needed.
    # For now, we'll just return a UUID and rely on message metadata for session tracking.
    logger.info(f"Created new session: {session_id} for user: {user_id}")
    return session_id

async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve session information.
    """
    # In a LanceDB-only setup, session info might be inferred from messages
    # or stored as a special entry. For now, we'll return a basic structure.
    # A more robust solution would involve a dedicated LanceDB table for sessions.
    # This is a placeholder.
    if session_id:
        # Check if any messages exist for this session
        # For now, return a basic session structure
        return {
            "id": session_id,
            "user_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"source": "lancedb_session"}
        }
    return None

async def add_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Add a message to the session.
    """
    # For LanceDB, messages are not stored in a separate table.
    # They are part of the agent's memory or can be stored as separate documents
    # if they are to be searchable. For now, this is a placeholder.
    # A more robust solution would involve Mem0 integration for persistent memory.
    logger.debug(f"Adding message to session {session_id}: {role}: {content[:50]}...")
    # This message would typically be stored in Mem0 or a dedicated message store.
    # For now, we'll just log it.
    pass # Mem0 will handle this in Phase 3

async def get_session_messages(
    session_id: str,
    limit: int = 10
) -> List[Dict[str, str]]:
    """
    Get recent messages for a session.
    """
    # This function would retrieve messages from Mem0.
    # For now, it returns a dummy message to allow the agent to run.
    logger.debug(f"Retrieving {limit} messages for session {session_id}")
    return [] # Mem0 will handle this in Phase 3
