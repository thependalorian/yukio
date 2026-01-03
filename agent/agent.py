"""
Main Pydantic AI agent for Yukio Japanese Tutor.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from .prompts import SYSTEM_PROMPT
from .providers import get_llm_model
from .tools import (
    vector_search_tool,
    hybrid_search_tool,
    get_document_tool,
    list_documents_tool,
    memory_search_tool,
    record_learning_tool,
    get_progress_tool,
    VectorSearchInput,
    HybridSearchInput,
    DocumentInput,
    DocumentListInput,
    MemorySearchInput,
    RecordLearningInput
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class AgentDependencies:
    """Dependencies for the agent."""
    session_id: str
    user_id: Optional[str] = None
    search_preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.search_preferences is None:
            self.search_preferences = {
                "use_vector": True,
                "default_limit": 10
            }


# Initialize the agent with flexible model configuration
rag_agent = Agent(
    get_llm_model(),
    deps_type=AgentDependencies,
    system_prompt=SYSTEM_PROMPT
)


# Register tools with proper docstrings (no description parameter)
@rag_agent.tool
async def vector_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for relevant information using semantic similarity.
    
    This tool performs vector similarity search across document chunks
    to find semantically related content. Returns the most relevant results
    regardless of similarity score.
    
    Args:
        query: Search query to find similar content
        limit: Maximum number of results to return (1-50)
    
    Returns:
        List of matching chunks ordered by similarity (best first)
    """
    input_data = VectorSearchInput(
        query=query,
        limit=limit
    )
    
    results = await vector_search_tool(input_data)
    
    # Convert results to dict for agent
    return [
        {
            "content": r.content,
            "score": r.score,
            "document_title": r.document_title,
            "document_source": r.document_source,
            "chunk_id": r.chunk_id
        }
        for r in results
    ]


@rag_agent.tool
async def hybrid_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10,
    text_weight: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Perform both vector and keyword search for comprehensive results.
    
    This tool combines semantic similarity search with keyword matching
    for the best coverage. It ranks results using both vector similarity
    and text matching scores. Best for combining semantic and exact matching.
    
    Args:
        query: Search query for hybrid search
        limit: Maximum number of results to return (1-50)
        text_weight: Weight for text similarity vs vector similarity (0.0-1.0)
    
    Returns:
        List of chunks ranked by combined relevance score
    """
    input_data = HybridSearchInput(
        query=query,
        limit=limit,
        text_weight=text_weight
    )
    
    results = await hybrid_search_tool(input_data)
    
    # Convert results to dict for agent
    return [
        {
            "content": r.content,
            "score": r.score,
            "document_title": r.document_title,
            "document_source": r.document_source,
            "chunk_id": r.chunk_id
        }
        for r in results
    ]


@rag_agent.tool
async def get_document(
    ctx: RunContext[AgentDependencies],
    document_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the complete content of a specific document.
    
    This tool fetches the full document content along with all its chunks
    and metadata. Best for getting comprehensive information from a specific
    source when you need the complete context.
    
    Args:
        document_id: UUID of the document to retrieve
    
    Returns:
        Complete document data with content and metadata, or None if not found
    """
    input_data = DocumentInput(document_id=document_id)
    
    document = await get_document_tool(input_data)
    
    if document:
        # Format for agent consumption
        return {
            "id": document["id"],
            "title": document["title"],
            "source": document["source"],
            "content": document["content"],
            "chunk_count": len(document.get("chunks", [])),
            "created_at": document["created_at"]
        }
    
    return None


@rag_agent.tool
async def list_documents(
    ctx: RunContext[AgentDependencies],
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    List available documents with their metadata.
    
    This tool provides an overview of all documents in the knowledge base,
    including titles, sources, and chunk counts. Best for understanding
    what information sources are available.
    
    Args:
        limit: Maximum number of documents to return (1-100)
        offset: Number of documents to skip for pagination
    
    Returns:
        List of documents with metadata and chunk counts
    """
    input_data = DocumentListInput(limit=limit, offset=offset)
    
    documents = await list_documents_tool(input_data)
    
    # Convert to dict for agent
    return [
        {
            "id": d.id,
            "title": d.title,
            "source": d.source,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat()
        }
        for d in documents
    ]


@rag_agent.tool
async def search_memory(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search the student's learning memory for previous lessons and progress.
    
    This tool searches the student's learning history to find what they've
    learned, mistakes they've made, and their progress. Useful for personalizing
    lessons and identifying areas that need review.
    
    Args:
        query: What to search for in the student's memory
        limit: Maximum number of results to return
    
    Returns:
        List of relevant memories from the student's learning history
    """
    input_data = MemorySearchInput(query=query, limit=limit)
    results = await memory_search_tool(input_data)
    return results


@rag_agent.tool
async def record_learning(
    ctx: RunContext[AgentDependencies],
    learning_type: str,
    content: str,
    details: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Record what the student has learned.
    
    This tool saves learning progress to the student's memory. Use this when
    the student successfully learns something new (vocabulary, kanji, grammar).
    
    Args:
        learning_type: Type of learning (kanji, vocabulary, grammar, or general)
        content: What was learned
        details: Additional details about the learning
    
    Returns:
        Confirmation of what was recorded
    """
    input_data = RecordLearningInput(
        learning_type=learning_type,
        content=content,
        details=details
    )
    return await record_learning_tool(input_data)


@rag_agent.tool
async def get_student_progress(
    ctx: RunContext[AgentDependencies]
) -> Dict[str, Any]:
    """
    Get the student's overall learning progress.
    
    This tool retrieves comprehensive progress information including kanji
    learned, vocabulary mastered, grammar points covered, and areas that
    need improvement.
    
    Returns:
        Dictionary with progress statistics and recommendations
    """
    return await get_progress_tool()