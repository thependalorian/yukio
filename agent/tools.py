"""
Tools for the Yukio Japanese Tutor AI agent.

This module provides RAG (Retrieval-Augmented Generation) tools optimized
for Japanese language learning. Uses LanceDB for vector storage and Mem0
for conversation memory.

Available Tools:
- vector_search_tool: Semantic similarity search across Japanese learning materials
- hybrid_search_tool: Combined vector + keyword search
- get_document_tool: Retrieve complete document content
- list_documents_tool: List available learning materials
- memory_search_tool: Search student's learning history
- record_learning_tool: Record what the student has learned
- get_progress_tool: Get student's learning progress

Usage:
    from agent.tools import vector_search_tool, VectorSearchInput

    results = await vector_search_tool(
        VectorSearchInput(query="hiragana basics", limit=10)
    )
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .db_utils import (
    db_manager
)
from .memory_utils import get_memory, recall, get_progress
from .models import ChunkResult, DocumentMetadata
from .providers import get_embedding_client, get_embedding_model

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize embedding client with flexible provider
embedding_client = get_embedding_client()
EMBEDDING_MODEL = get_embedding_model()


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using the configured embedding provider.

    Uses the embedding client from providers module which supports multiple
    providers (OpenAI, Ollama, etc.) based on environment configuration.

    Args:
        text: Text to embed (will be converted to embedding vector)

    Returns:
        Embedding vector as list of floats

    Raises:
        Exception: If embedding generation fails
    """
    try:
        response = await embedding_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        raise


# Tool Input Models
class VectorSearchInput(BaseModel):
    """Input for vector search tool."""
    query: str = Field(..., description="Search query in English or Japanese")
    limit: int = Field(default=10, description="Maximum number of results")


class HybridSearchInput(BaseModel):
    """Input for hybrid search tool."""
    query: str = Field(..., description="Search query in English or Japanese")
    limit: int = Field(default=10, description="Maximum number of results")
    text_weight: float = Field(default=0.3, description="Weight for text similarity (0-1)")


class DocumentInput(BaseModel):
    """Input for document retrieval."""
    document_id: str = Field(..., description="Document ID to retrieve")


class DocumentListInput(BaseModel):
    """Input for listing documents."""
    limit: int = Field(default=20, description="Maximum number of documents")
    offset: int = Field(default=0, description="Number of documents to skip")


class MemorySearchInput(BaseModel):
    """Input for memory search."""
    query: str = Field(..., description="What to search for in student's memory")
    limit: int = Field(default=10, description="Maximum results")


class RecordLearningInput(BaseModel):
    """Input for recording learning progress."""
    learning_type: str = Field(..., description="Type: kanji, vocabulary, grammar, or general")
    content: str = Field(..., description="What was learned")
    details: Optional[Dict[str, str]] = Field(None, description="Additional details")


class RecordMistakeInput(BaseModel):
    """Input for recording a mistake."""
    mistake_type: str = Field(..., description="Type of mistake")
    details: str = Field(..., description="What the mistake was")
    correction: str = Field(..., description="The correct answer")


# Tool Implementation Functions
async def vector_search_tool(input_data: VectorSearchInput) -> List[ChunkResult]:
    """
    Perform vector similarity search on Japanese learning materials.

    Args:
        input_data: Search parameters

    Returns:
        List of matching chunks from learning materials
    """
    try:
        # Generate embedding for the query
        embedding = await generate_embedding(input_data.query)

        # Perform vector search
        results = db_manager.vector_search(
            embedding=embedding,
            limit=input_data.limit
        )

        # Convert to ChunkResult models
        # LanceDB returns 'id' not 'chunk_id', and '_distance' not 'similarity'
        chunk_results = []
        for r in results:
            try:
                # Safely extract fields - LanceDB uses 'id' not 'chunk_id'
                chunk_id = str(r.get("id", "")) if isinstance(r, dict) else ""
                if not chunk_id:
                    logger.warning(f"Skipping result with missing 'id' field: {r}")
                    continue
                
                # Extract distance and convert to similarity score
                distance = r.get("_distance", 0.0)
                if isinstance(distance, (int, float)):
                    # Convert distance to similarity (0-1 scale, higher is better)
                    # Distance is typically 0-2, so similarity = 1 - (distance / 2)
                    score = max(0.0, min(1.0, 1.0 - (float(distance) / 2.0)))
                else:
                    score = 0.0
                
                # Extract metadata - already parsed as dict by db_utils
                metadata = r.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                chunk_results.append(
                    ChunkResult(
                        chunk_id=chunk_id,
                        document_id=str(r.get("document_id", "")),
                        content=str(r.get("content", r.get("text", ""))),
                        score=score,
                        metadata=metadata,
                        document_title=str(r.get("document_title", r.get("title", "Unknown"))),
                        document_source=str(r.get("document_source", r.get("source", "")))
                    )
                )
            except Exception as e:
                logger.warning(f"Error processing search result: {e}, result: {r}")
                continue
        
        return chunk_results

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []


async def hybrid_search_tool(input_data: HybridSearchInput) -> List[ChunkResult]:
    """
    Perform hybrid search combining vector similarity and keyword matching.

    Combines semantic similarity search with full-text keyword matching
    for comprehensive search results. Useful for Japanese text which may
    have exact character matches (kanji) alongside semantic meaning.

    Args:
        input_data: Search parameters including query, limit, and text weight

    Returns:
        List of matching chunks ordered by combined score (best first)
    """
    try:
        # Generate embedding for the query
        embedding = await generate_embedding(input_data.query)

        # Perform hybrid search
        results = db_manager.hybrid_search(
            embedding=embedding,
            query_text=input_data.query,
            limit=input_data.limit,
            text_weight=input_data.text_weight
        )

        # Convert to ChunkResult models
        # LanceDB returns 'id' not 'chunk_id', and '_distance' not 'similarity'
        chunk_results = []
        for r in results:
            try:
                # Safely extract fields - LanceDB uses 'id' not 'chunk_id'
                chunk_id = str(r.get("id", "")) if isinstance(r, dict) else ""
                if not chunk_id:
                    logger.warning(f"Skipping result with missing 'id' field: {r}")
                    continue
                
                # Extract distance and convert to similarity score
                distance = r.get("_distance", 0.0)
                if isinstance(distance, (int, float)):
                    # Convert distance to similarity (0-1 scale, higher is better)
                    score = max(0.0, min(1.0, 1.0 - (float(distance) / 2.0)))
                else:
                    # Try other score fields
                    score = float(r.get("combined_score", r.get("similarity", 0.0)))
                
                # Extract metadata - already parsed as dict by db_utils
                metadata = r.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                
                chunk_results.append(
                    ChunkResult(
                        chunk_id=chunk_id,
                        document_id=str(r.get("document_id", "")),
                        content=str(r.get("content", r.get("text", ""))),
                        score=score,
                        metadata=metadata,
                        document_title=str(r.get("document_title", r.get("title", "Unknown"))),
                        document_source=str(r.get("document_source", r.get("source", "")))
                    )
                )
            except Exception as e:
                logger.warning(f"Error processing hybrid search result: {e}, result: {r}")
                continue
        
        return chunk_results

    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        return []


async def get_document_tool(input_data: DocumentInput) -> Optional[Dict[str, Any]]:
    """
    Retrieve a complete document from the learning materials.

    Args:
        input_data: Document retrieval parameters

    Returns:
        Document data or None
    """
    try:
        # Get all chunks for the document
        chunks = db_manager.get_document_chunks(input_data.document_id)
        
        if chunks:
            # Build document from chunks
            first_chunk = chunks[0]
            document = {
                "id": first_chunk.get("document_id"),
                "title": first_chunk.get("document_title"),
                "source": first_chunk.get("document_source"),
                "chunks": chunks,
                "chunk_count": len(chunks)
            }
            return document
        
        return None

    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return None


async def list_documents_tool(input_data: DocumentListInput) -> List[DocumentMetadata]:
    """
    List available Japanese learning materials.

    Args:
        input_data: Listing parameters

    Returns:
        List of document metadata
    """
    try:
        documents = db_manager.list_documents(
            limit=input_data.limit,
            offset=input_data.offset
        )

        # Convert to DocumentMetadata models
        return [
            DocumentMetadata(
                id=d["id"],
                title=d["title"],
                source=d["source"],
                metadata=d["metadata"],
                created_at=datetime.fromisoformat(d["created_at"]) if isinstance(d["created_at"], str) else d["created_at"],
                updated_at=datetime.fromisoformat(d["updated_at"]) if isinstance(d["updated_at"], str) else d["updated_at"],
                chunk_count=d.get("chunk_count")
            )
            for d in documents
        ]

    except Exception as e:
        logger.error(f"Document listing failed: {e}")
        return []


async def memory_search_tool(input_data: MemorySearchInput) -> List[Dict[str, Any]]:
    """
    Search the student's learning memory.

    Useful for:
    - Finding what kanji/vocabulary the student already knows
    - Checking previous mistakes that need review
    - Retrieving student preferences

    Args:
        input_data: Memory search parameters

    Returns:
        List of relevant memories
    """
    try:
        return recall(input_data.query, input_data.limit)
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return []


async def record_learning_tool(input_data: RecordLearningInput) -> Dict[str, Any]:
    """
    Record what the student has learned.

    Args:
        input_data: Learning record parameters

    Returns:
        Result of recording
    """
    try:
        memory = get_memory()
        details = input_data.details or {}

        if input_data.learning_type == "kanji":
            return memory.record_kanji_learned(
                kanji=details.get("kanji", input_data.content),
                reading=details.get("reading", ""),
                meaning=details.get("meaning", ""),
                example=details.get("example")
            )
        elif input_data.learning_type == "vocabulary":
            return memory.record_vocabulary(
                word=details.get("word", input_data.content),
                reading=details.get("reading", ""),
                meaning=details.get("meaning", ""),
                jlpt_level=details.get("jlpt_level")
            )
        elif input_data.learning_type == "grammar":
            return memory.record_grammar_point(
                grammar=details.get("grammar", input_data.content),
                explanation=details.get("explanation", ""),
                example=details.get("example")
            )
        else:
            # General learning record
            return memory.add_memory(
                f"Student learned: {input_data.content}",
                metadata={
                    "type": input_data.learning_type,
                    **details
                }
            )

    except Exception as e:
        logger.error(f"Failed to record learning: {e}")
        return {"error": str(e)}


async def record_mistake_tool(input_data: RecordMistakeInput) -> Dict[str, Any]:
    """
    Record a mistake for future review.

    Args:
        input_data: Mistake details

    Returns:
        Result of recording
    """
    try:
        memory = get_memory()
        return memory.record_mistake(
            mistake_type=input_data.mistake_type,
            details=input_data.details,
            correction=input_data.correction
        )
    except Exception as e:
        logger.error(f"Failed to record mistake: {e}")
        return {"error": str(e)}


async def get_progress_tool() -> Dict[str, Any]:
    """
    Get the student's learning progress summary.

    Returns:
        Dictionary with progress statistics:
        - kanji_learned: Number of kanji learned
        - vocabulary_learned: Number of vocabulary words learned
        - grammar_points: Number of grammar points studied
        - mistakes_to_review: Number of mistakes needing review
    """
    try:
        return get_progress()
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        return {
            "error": str(e),
            "kanji_learned": 0,
            "vocabulary_learned": 0,
            "grammar_points": 0,
            "mistakes_to_review": 0
        }


async def get_review_items_tool(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get items that need review (mistakes, difficult content).

    Args:
        limit: Maximum number of items

    Returns:
        List of items needing review
    """
    try:
        memory = get_memory()
        return memory.get_review_items(limit)
    except Exception as e:
        logger.error(f"Failed to get review items: {e}")
        return []


# Combined search function for agent use
async def perform_comprehensive_search(
    query: str,
    use_vector: bool = True,
    use_memory: bool = True,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Perform a comprehensive search using multiple methods.

    Searches both the learning materials (LanceDB) and student memory (Mem0)
    to provide context-aware responses.

    Args:
        query: Search query
        use_vector: Whether to search learning materials
        use_memory: Whether to search student memory
        limit: Maximum results per search type

    Returns:
        Combined search results with learning materials and memories
    """
    results = {
        "query": query,
        "learning_materials": [],
        "student_memories": [],
        "total_results": 0
    }

    tasks = []

    if use_vector:
        tasks.append(vector_search_tool(VectorSearchInput(query=query, limit=limit)))

    if use_memory:
        tasks.append(memory_search_tool(MemorySearchInput(query=query, limit=limit)))

    if tasks:
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        if use_vector and not isinstance(search_results[0], Exception):
            results["learning_materials"] = search_results[0]

        if use_memory:
            memory_idx = 1 if use_vector else 0
            if not isinstance(search_results[memory_idx], Exception):
                results["student_memories"] = search_results[memory_idx]

    results["total_results"] = len(results["learning_materials"]) + len(results["student_memories"])

    return results
