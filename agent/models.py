"""
Pydantic models for data validation and serialization.
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SearchType(str, Enum):
    """Search type enumeration."""
    VECTOR = "vector"
    HYBRID = "hybrid"
    GRAPH = "graph"


# Request Models
class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_id: Optional[str] = Field(None, description="User identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    search_type: SearchType = Field(default=SearchType.HYBRID, description="Type of search to perform")
    
    model_config = ConfigDict(use_enum_values=True)


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query")
    search_type: SearchType = Field(default=SearchType.HYBRID, description="Type of search")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    
    model_config = ConfigDict(use_enum_values=True)


# Response Models
class DocumentMetadata(BaseModel):
    """Document metadata model."""
    id: str
    title: str
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    chunk_count: Optional[int] = None


class ChunkResult(BaseModel):
    """Chunk search result model."""
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    document_title: str
    document_source: str
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is between 0 and 1."""
        return max(0.0, min(1.0, v))


class GraphSearchResult(BaseModel):
    """Knowledge graph search result model."""
    fact: str
    uuid: str
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    source_node_uuid: Optional[str] = None


class EntityRelationship(BaseModel):
    """Entity relationship model."""
    from_entity: str
    to_entity: str
    relationship_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Search response model."""
    results: List[ChunkResult] = Field(default_factory=list)
    graph_results: List[GraphSearchResult] = Field(default_factory=list)
    total_results: int = 0
    search_type: SearchType
    query_time_ms: float


class ToolCall(BaseModel):
    """Tool call information model."""
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    tool_call_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    message: str
    session_id: str
    sources: List[DocumentMetadata] = Field(default_factory=list)
    tools_used: List[ToolCall] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamDelta(BaseModel):
    """Streaming response delta."""
    content: str
    delta_type: Literal["text", "tool_call", "end"] = "text"
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Database Models
class Document(BaseModel):
    """Document model."""
    id: Optional[str] = None
    title: str
    source: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Chunk(BaseModel):
    """Document chunk model."""
    id: Optional[str] = None
    document_id: str
    content: str
    embedding: Optional[List[float]] = None
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_count: Optional[int] = None
    created_at: Optional[datetime] = None

    @field_validator('embedding')
    @classmethod
    def validate_embedding(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """
        Validate embedding dimensions.

        Supports multiple embedding models:
        - nomic-embed-text: 768 dimensions (Ollama local)
        - mxbai-embed-large: 1024 dimensions (Ollama local)
        - text-embedding-3-small: 1536 dimensions (OpenAI)
        - text-embedding-3-large: 3072 dimensions (OpenAI)
        """
        import os
        expected_dim = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
        if v is not None and len(v) != expected_dim:
            raise ValueError(f"Embedding must have {expected_dim} dimensions, got {len(v)}")
        return v


class Session(BaseModel):
    """Session model."""
    id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class Message(BaseModel):
    """Message model."""
    id: Optional[str] = None
    session_id: str
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(use_enum_values=True)


# Agent Models
class AgentDependencies(BaseModel):
    """Dependencies for the Yukio Japanese tutor agent."""
    session_id: str
    user_id: Optional[str] = None  # Student ID for personalized memory
    lancedb_path: Optional[str] = None  # Path to LanceDB
    mem0_path: Optional[str] = None  # Path to Mem0 storage

    model_config = ConfigDict(arbitrary_types_allowed=True)




class AgentContext(BaseModel):
    """Agent execution context."""
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    search_results: List[ChunkResult] = Field(default_factory=list)
    graph_results: List[GraphSearchResult] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Ingestion Models
class IngestionConfig(BaseModel):
    """Configuration for document ingestion."""
    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    max_chunk_size: int = Field(default=2000, ge=500, le=10000)
    use_semantic_chunking: bool = True
    extract_entities: bool = True
    # New option for faster ingestion
    skip_graph_building: bool = Field(default=False, description="Skip knowledge graph building for faster ingestion")
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        """Ensure overlap is less than chunk size."""
        chunk_size = info.data.get('chunk_size', 1000)
        if v >= chunk_size:
            raise ValueError(f"Chunk overlap ({v}) must be less than chunk size ({chunk_size})")
        return v


class IngestionResult(BaseModel):
    """Result of document ingestion."""
    document_id: str
    title: str
    chunks_created: int
    entities_extracted: int
    relationships_created: int
    processing_time_ms: float
    errors: List[str] = Field(default_factory=list)


# Error Models
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    error_type: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


# Health Check Models
class HealthStatus(BaseModel):
    """Health check status."""
    status: Literal["healthy", "degraded", "unhealthy"]
    lancedb: bool  # LanceDB vector database
    memory: bool  # Mem0 memory layer
    llm_connection: bool  # Ollama LLM
    version: str
    timestamp: datetime


# User Progress Models
class UserProgress(BaseModel):
    """User progress model for gamification."""
    user_id: str
    name: str = "Student"
    level: int = 1
    xp: int = 0
    xp_to_next_level: int = 100
    streak: int = 0
    daily_goal: int = 20
    hearts: int = 3
    jlpt_level: str = "N5"
    lessons_completed: int = 0
    vocab_mastered: int = 0


class ProgressRecord(BaseModel):
    """Individual progress record."""
    user_id: str
    progress_type: Literal["lesson", "vocab", "quiz", "xp", "streak"]
    item_id: str
    status: Literal["completed", "in_progress", "locked", "mastered"]
    data: Dict[str, Any] = Field(default_factory=dict)
    xp_earned: int = 0
    crowns: int = 0


# Learning Content Models
class Lesson(BaseModel):
    """Lesson model."""
    id: str
    title: str
    titleJP: Optional[str] = None
    description: str
    xp: int
    crowns: int
    status: Literal["locked", "available", "in-progress", "completed"] = "available"
    jlpt: Literal["N5", "N4", "N3", "N2", "N1"] = "N5"
    category: Literal["hiragana", "katakana", "kanji", "grammar", "vocabulary"]
    content: Optional[str] = None  # Full lesson content


class VocabWord(BaseModel):
    """Vocabulary word model."""
    id: str
    japanese: str
    reading: str
    romaji: str
    english: str
    example: Optional[str] = None
    exampleReading: Optional[str] = None
    exampleTranslation: Optional[str] = None
    jlpt: str


class QuizQuestion(BaseModel):
    """Quiz question model."""
    id: str
    type: Literal["multiple-choice", "type-answer", "match", "listen"]
    question: str
    questionJP: Optional[str] = None
    options: Optional[List[str]] = None
    correctAnswer: str
    explanation: Optional[str] = None
    audioUrl: Optional[str] = None


class VoicePhrase(BaseModel):
    """Voice practice phrase model."""
    id: str
    japanese: str
    romaji: str
    english: str
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    category: str