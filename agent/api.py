"""
FastAPI endpoints for the Yukio Japanese Tutor.
"""

import os
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import aiohttp
from dotenv import load_dotenv

from .agent import rag_agent, AgentDependencies
from .db_utils import (
    initialize_database,
    close_database,
    create_session,
    get_session,
    add_message,
    get_session_messages,
    test_connection,
    db_manager
)
from .models import (
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    StreamDelta,
    ErrorResponse,
    HealthStatus,
    ToolCall,
    UserProgress,
    ProgressRecord,
    Lesson,
    VocabWord,
    QuizQuestion,
    VoicePhrase
)
from .tools import (
    vector_search_tool,
    hybrid_search_tool,
    list_documents_tool,
    VectorSearchInput,
    HybridSearchInput,
    DocumentListInput
)
from .tts import TTSManager
from fastapi.responses import Response
import io
import numpy as np

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Application configuration
APP_ENV = os.getenv("APP_ENV", "development")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8058))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Global TTS manager (initialized in lifespan)
tts_manager: Optional[TTSManager] = None

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Set debug level for our module during development
if APP_ENV == "development":
    logger.setLevel(logging.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Startup
    logger.info("Starting up Yukio Japanese Tutor API...")
    
    try:
        # Initialize database connections
        await initialize_database()
        logger.info("Database initialized")
        
        # Ensure user progress table exists
        db_manager.create_user_progress_table()
        logger.info("User progress table ready")
        
        # Initialize TTS manager (optional, won't break if unavailable)
        global tts_manager
        try:
            tts_manager = TTSManager()
            if tts_manager.is_available():
                logger.info("TTS (Dia) initialized and available")
            else:
                logger.info("TTS (Dia) not available - voice features disabled")
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")
            tts_manager = None
        
        # Test connections
        db_ok = await test_connection()
        
        if not db_ok:
            logger.error("Database connection failed")
        
        logger.info("Yukio API startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Yukio API...")
    
    try:
        await close_database()
        logger.info("Connections closed")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Yukio Japanese Tutor API",
    description="AI-powered Japanese language tutor with local LLM and vector search",
    version="0.1.0",
    lifespan=lifespan
)

# Add middleware with flexible CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Helper functions for agent execution
async def get_or_create_session(request: ChatRequest) -> str:
    """Get existing session or create new one."""
    if request.session_id:
        session = await get_session(request.session_id)
        if session:
            return request.session_id
    
    # Create new session
    return await create_session(
        user_id=request.user_id,
        metadata=request.metadata
    )


async def get_conversation_context(
    session_id: str,
    max_messages: int = 10
) -> List[Dict[str, str]]:
    """
    Get recent conversation context.
    
    Args:
        session_id: Session ID
        max_messages: Maximum number of messages to retrieve
    
    Returns:
        List of messages
    """
    messages = await get_session_messages(session_id, limit=max_messages)
    
    return [
        {
            "role": msg["role"],
            "content": msg["content"]
        }
        for msg in messages
    ]


def clean_agent_response(response: str) -> str:
    """
    Clean agent response to remove raw search results and metadata.
    
    Removes common patterns where the LLM includes raw search results,
    document references, or metadata in the response.
    
    Args:
        response: Raw agent response
    
    Returns:
        Cleaned response without search result references
    """
    import re
    
    # Patterns to remove (Japanese and English)
    patterns_to_remove = [
        # Japanese patterns
        r'これらのドキュメントの検索結果[は、].*?(?=\n\n|\n[A-Z]|$)',
        r'以下にいくつか重要な内容を抜粋します[：:].*?(?=\n\n|\n[A-Z]|$)',
        r'検索結果[は、].*?(?=\n\n|\n[A-Z]|$)',
        r'ドキュメント.*?から得られます.*?(?=\n\n|\n[A-Z]|$)',
        r'主に.*?資料から得られます.*?(?=\n\n|\n[A-Z]|$)',
        # English patterns
        r'Search results.*?(?=\n\n|\n[A-Z]|$)',
        r'Based on.*?search.*?results.*?(?=\n\n|\n[A-Z]|$)',
        r'From the.*?documents.*?(?=\n\n|\n[A-Z]|$)',
        r'Document.*?sources.*?(?=\n\n|\n[A-Z]|$)',
        # Metadata patterns
        r'chunk_id[:\s]+[a-f0-9-]+',
        r'document_id[:\s]+[a-f0-9-]+',
        r'score[:\s]+[\d.]+',
        r'\(Source:.*?\)',
        r'\[Source:.*?\]',
    ]
    
    cleaned = response
    for pattern in patterns_to_remove:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE)
    
    # Remove multiple consecutive newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def extract_tool_calls(result) -> List[ToolCall]:
    """
    Extract tool calls from Pydantic AI result.
    
    Args:
        result: Pydantic AI result object
    
    Returns:
        List of ToolCall objects
    """
    tools_used = []
    
    try:
        # Get all messages from the result
        messages = result.all_messages()
        
        for message in messages:
            if hasattr(message, 'parts'):
                for part in message.parts:
                    # Check if this is a tool call part
                    if part.__class__.__name__ == 'ToolCallPart':
                        try:
                            # Debug logging to understand structure
                            logger.debug(f"ToolCallPart attributes: {dir(part)}")
                            logger.debug(f"ToolCallPart content: tool_name={getattr(part, 'tool_name', None)}")
                            
                            # Extract tool information safely
                            tool_name = str(part.tool_name) if hasattr(part, 'tool_name') else 'unknown'
                            
                            # Get args - the args field is a JSON string in Pydantic AI
                            tool_args = {}
                            if hasattr(part, 'args') and part.args is not None:
                                if isinstance(part.args, str):
                                    # Args is a JSON string, parse it
                                    try:
                                        import json
                                        tool_args = json.loads(part.args)
                                        logger.debug(f"Parsed args from JSON string: {tool_args}")
                                    except json.JSONDecodeError as e:
                                        logger.debug(f"Failed to parse args JSON: {e}")
                                        tool_args = {}
                                elif isinstance(part.args, dict):
                                    tool_args = part.args
                                    logger.debug(f"Args already a dict: {tool_args}")
                            
                            # Alternative: use args_as_dict method if available
                            if hasattr(part, 'args_as_dict'):
                                try:
                                    tool_args = part.args_as_dict()
                                    logger.debug(f"Got args from args_as_dict(): {tool_args}")
                                except:
                                    pass
                            
                            # Get tool call ID
                            tool_call_id = None
                            if hasattr(part, 'tool_call_id'):
                                tool_call_id = str(part.tool_call_id) if part.tool_call_id else None
                            
                            # Create ToolCall with explicit field mapping
                            tool_call_data = {
                                "tool_name": tool_name,
                                "args": tool_args,
                                "tool_call_id": tool_call_id
                            }
                            logger.debug(f"Creating ToolCall with data: {tool_call_data}")
                            tools_used.append(ToolCall(**tool_call_data))
                        except Exception as e:
                            logger.debug(f"Failed to parse tool call part: {e}")
                            continue
    except Exception as e:
        logger.warning(f"Failed to extract tool calls: {e}")
    
    return tools_used


async def save_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Save a conversation turn to the database.
    
    Args:
        session_id: Session ID
        user_message: User's message
        assistant_message: Assistant's response
        metadata: Optional metadata
    """
    # Save user message
    await add_message(
        session_id=session_id,
        role="user",
        content=user_message,
        metadata=metadata or {}
    )
    
    # Save assistant message
    await add_message(
        session_id=session_id,
        role="assistant",
        content=assistant_message,
        metadata=metadata or {}
    )


async def execute_agent(
    message: str,
    session_id: str,
    user_id: Optional[str] = None,
    save_conversation: bool = True
) -> tuple[str, List[ToolCall]]:
    """
    Execute the agent with a message.
    
    Args:
        message: User message
        session_id: Session ID
        user_id: Optional user ID
        save_conversation: Whether to save the conversation
    
    Returns:
        Tuple of (agent response, tools used)
    """
    try:
        # Create dependencies
        deps = AgentDependencies(
            session_id=session_id,
            user_id=user_id
        )
        
        # Get conversation context
        context = await get_conversation_context(session_id)
        
        # Build prompt with context
        full_prompt = message
        if context:
            context_str = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in context[-6:]  # Last 3 turns
            ])
            full_prompt = f"Previous conversation:\n{context_str}\n\nCurrent question: {message}"
        
        # Run the agent
        result = await rag_agent.run(full_prompt, deps=deps)
        
        # Get response - PydanticAI returns result.data
        response = result.data if hasattr(result, 'data') else str(result)
        tools_used = extract_tool_calls(result)
        
        # Save conversation if requested
        if save_conversation:
            await save_conversation_turn(
                session_id=session_id,
                user_message=message,
                assistant_message=response,
                metadata={
                    "user_id": user_id,
                    "tool_calls": len(tools_used)
                }
            )
        
        return response, tools_used
        
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        error_response = f"I encountered an error while processing your request: {str(e)}"
        
        if save_conversation:
            await save_conversation_turn(
                session_id=session_id,
                user_message=message,
                assistant_message=error_response,
                metadata={"error": str(e)}
            )
        
        return error_response, []


# API Endpoints
@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connections
        lancedb_status = await test_connection()
        
        # Test memory (Mem0) - optional, so we check if it's available
        memory_status = False
        try:
            from agent.memory_utils import get_memory
            # Just check if memory module can be imported and initialized
            memory_status = True
        except Exception:
            # Memory is optional, so False is acceptable
            memory_status = False
        
        # Test LLM connection (Ollama) - try a simple check
        llm_status = True  # Assume OK if we can respond
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:11434/api/tags", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    llm_status = response.status == 200
        except Exception:
            llm_status = False
        
        # Determine overall status
        if lancedb_status and llm_status:
            status = "healthy"
        elif lancedb_status or llm_status:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return HealthStatus(
            status=status,
            lancedb=lancedb_status,
            memory=memory_status,
            llm_connection=llm_status,
            version="0.1.0",
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    try:
        # Get or create session
        session_id = await get_or_create_session(request)
        
        # Execute agent
        response, tools_used = await execute_agent(
            message=request.message,
            session_id=session_id,
            user_id=request.user_id
        )
        
        return ChatResponse(
            message=response,
            session_id=session_id,
            tools_used=tools_used,
            metadata={"search_type": str(request.search_type)}
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint using Server-Sent Events."""
    try:
        # Get or create session
        session_id = await get_or_create_session(request)
        
        async def generate_stream():
            """Generate streaming response using agent.iter() pattern."""
            try:
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # Create dependencies
                deps = AgentDependencies(
                    session_id=session_id,
                    user_id=request.user_id
                )
                
                # Get conversation context
                context = await get_conversation_context(session_id)
                
                # Build input with context
                full_prompt = request.message
                if context:
                    context_str = "\n".join([
                        f"{msg['role']}: {msg['content']}"
                        for msg in context[-6:]
                    ])
                    full_prompt = f"Previous conversation:\n{context_str}\n\nCurrent question: {request.message}"
                
                # Save user message immediately
                await add_message(
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    metadata={"user_id": request.user_id}
                )
                
                full_response = ""
                
                # Stream using agent.iter() pattern
                async with rag_agent.iter(full_prompt, deps=deps) as run:
                    async for node in run:
                        if rag_agent.is_model_request_node(node):
                            # Stream tokens from the model
                            async with node.stream(run.ctx) as request_stream:
                                async for event in request_stream:
                                    from pydantic_ai.messages import PartStartEvent, PartDeltaEvent, TextPartDelta
                                    
                                    if isinstance(event, PartStartEvent) and event.part.part_kind == 'text':
                                        delta_content = event.part.content
                                        yield f"data: {json.dumps({'type': 'text_delta', 'text': delta_content})}\n\n"
                                        full_response += delta_content
                                        
                                    elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                                        delta_content = event.delta.content_delta
                                        yield f"data: {json.dumps({'type': 'text_delta', 'text': delta_content})}\n\n"
                                        full_response += delta_content
                
                # Extract tools used from the final result
                result = run.result
                tools_used = extract_tool_calls(result)
                
                # Send tools used information
                if tools_used:
                    tools_data = [
                        {
                            "tool_name": tool.tool_name,
                            "args": tool.args,
                            "tool_call_id": tool.tool_call_id
                        }
                        for tool in tools_used
                    ]
                    yield f"data: {json.dumps({'type': 'tools', 'tools': tools_data})}\n\n"
                
                # Clean response - remove any raw search result references
                cleaned_response = clean_agent_response(full_response)
                
                # Save assistant response
                await add_message(
                    session_id=session_id,
                    role="assistant",
                    content=cleaned_response,
                    metadata={
                        "streamed": True,
                        "tool_calls": len(tools_used)
                    }
                )
                
                yield f"data: {json.dumps({'type': 'end'})}\n\n"
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_chunk = {
                    "type": "error",
                    "content": f"Stream error: {str(e)}"
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/vector")
async def search_vector(request: SearchRequest):
    """Vector search endpoint."""
    try:
        input_data = VectorSearchInput(
            query=request.query,
            limit=request.limit
        )
        
        start_time = datetime.now()
        results = await vector_search_tool(input_data)
        end_time = datetime.now()
        
        query_time = (end_time - start_time).total_seconds() * 1000
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            search_type="vector",
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/hybrid")
async def search_hybrid(request: SearchRequest):
    """Hybrid search endpoint."""
    try:
        input_data = HybridSearchInput(
            query=request.query,
            limit=request.limit
        )
        
        start_time = datetime.now()
        results = await hybrid_search_tool(input_data)
        end_time = datetime.now()
        
        query_time = (end_time - start_time).total_seconds() * 1000
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            search_type="hybrid",
            query_time_ms=query_time
        )
        
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents")
async def list_documents_endpoint(
    limit: int = 20,
    offset: int = 0
):
    """List documents endpoint."""
    try:
        input_data = DocumentListInput(limit=limit, offset=offset)
        documents = await list_documents_tool(input_data)
        
        return {
            "documents": documents,
            "total": len(documents),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Document listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get session information."""
    try:
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/progress/{user_id}", response_model=UserProgress)
async def get_user_progress(user_id: str):
    """Get user progress statistics."""
    try:
        stats = db_manager.get_user_stats(user_id)
        return UserProgress(**stats)
    except Exception as e:
        logger.error(f"Failed to get user progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/progress/{user_id}/record")
async def record_progress(user_id: str, record: ProgressRecord):
    """Record user progress (lesson completion, vocab learned, etc.)."""
    try:
        progress_id = db_manager.record_user_progress(
            user_id=user_id,
            progress_type=record.progress_type,
            item_id=record.item_id,
            status=record.status,
            data=record.data,
            xp_earned=record.xp_earned,
            crowns=record.crowns
        )
        return {"id": progress_id, "status": "recorded"}
    except Exception as e:
        logger.error(f"Failed to record progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/progress/{user_id}/lessons")
async def get_user_lessons(user_id: str, progress_type: Optional[str] = None):
    """Get user's lesson/vocab progress records."""
    try:
        records = db_manager.get_user_progress(user_id, progress_type=progress_type)
        return {"records": records, "total": len(records)}
    except Exception as e:
        logger.error(f"Failed to get user lessons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lessons", response_model=List[Lesson])
async def get_lessons(
    category: Optional[str] = None,
    jlpt: Optional[str] = None,
    limit: int = 20
):
    """
    Generate lessons from ingested Japanese learning materials.
    Uses RAG to search the knowledge base and LLM to structure lessons.
    """
    try:
        session_id = str(uuid.uuid4())
        deps = AgentDependencies(session_id=session_id)
        
        # Build query based on filters
        query_parts = []
        if category:
            query_parts.append(f"{category} lessons")
        if jlpt:
            query_parts.append(f"JLPT {jlpt}")
        if not query_parts:
            query_parts.append("Japanese language lessons")
        
        query = " ".join(query_parts)
        
        # Use agent to generate structured lessons from RAG data
        prompt = f"""Generate a list of {limit} structured Japanese lessons from the learning materials.
        
Requirements:
- Each lesson should have: title, titleJP (Japanese title), description, xp (10-30), crowns (0-5), jlpt level, category
- Categories: hiragana, katakana, kanji, grammar, vocabulary
- JLPT levels: N5, N4, N3, N2, N1
- Status should be "available" for all
- Search the knowledge base for relevant content
- Return as JSON array of lesson objects

Query: {query}
Category filter: {category or 'all'}
JLPT filter: {jlpt or 'all'}
"""
        
        result = await rag_agent.run(prompt, deps=deps)
        
        # Parse LLM response (should be JSON)
        try:
            # Try to extract JSON from response
            response_text = result.output
            # Look for JSON array in response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                lessons_data = json.loads(response_text[json_start:json_end])
            else:
                # Fallback: try parsing entire response
                lessons_data = json.loads(response_text)
            
            # Convert to Lesson models
            lessons = []
            for i, lesson_data in enumerate(lessons_data[:limit]):
                lesson = Lesson(
                    id=str(uuid.uuid4()),
                    title=lesson_data.get("title", f"Lesson {i+1}"),
                    titleJP=lesson_data.get("titleJP"),
                    description=lesson_data.get("description", ""),
                    xp=lesson_data.get("xp", 15),
                    crowns=lesson_data.get("crowns", 0),
                    status="available",
                    jlpt=lesson_data.get("jlpt", "N5"),
                    category=lesson_data.get("category", "grammar")
                )
                lessons.append(lesson)
            
            return lessons
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse lesson JSON: {e}")
            logger.error(f"LLM response: {result.output[:500]}")
            # Return empty list if parsing fails
            return []
        
    except Exception as e:
        logger.error(f"Failed to generate lessons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vocabulary", response_model=List[VocabWord])
async def get_vocabulary(
    jlpt: Optional[str] = None,
    limit: int = 50
):
    """
    Extract vocabulary words from ingested Japanese learning materials.
    Uses RAG to find vocabulary and LLM to structure it.
    """
    try:
        session_id = str(uuid.uuid4())
        deps = AgentDependencies(session_id=session_id)
        
        query = f"Japanese vocabulary words"
        if jlpt:
            query += f" JLPT {jlpt}"
        
        prompt = f"""Extract {limit} Japanese vocabulary words from the learning materials.

For each word, provide:
- japanese: The word in Japanese (kanji/hiragana/katakana)
- reading: Hiragana reading
- romaji: Hepburn romanization
- english: English meaning
- example: Example sentence (optional)
- exampleReading: Hiragana reading of example (optional)
- exampleTranslation: English translation of example (optional)
- jlpt: JLPT level (N5-N1)

Search the knowledge base for vocabulary content.
Return as JSON array of vocabulary objects.

Query: {query}
JLPT filter: {jlpt or 'all'}
"""
        
        result = await rag_agent.run(prompt, deps=deps)
        
        import json
        try:
            response_text = result.output
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                vocab_data = json.loads(response_text[json_start:json_end])
            else:
                vocab_data = json.loads(response_text)
            
            vocab_words = []
            for i, word_data in enumerate(vocab_data[:limit]):
                word = VocabWord(
                    id=str(uuid.uuid4()),
                    japanese=word_data.get("japanese", ""),
                    reading=word_data.get("reading", ""),
                    romaji=word_data.get("romaji", ""),
                    english=word_data.get("english", ""),
                    example=word_data.get("example"),
                    exampleReading=word_data.get("exampleReading"),
                    exampleTranslation=word_data.get("exampleTranslation"),
                    jlpt=word_data.get("jlpt", "N5")
                )
                vocab_words.append(word)
            
            return vocab_words
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse vocabulary JSON: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Failed to generate vocabulary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/quiz/questions", response_model=List[QuizQuestion])
async def get_quiz_questions(
    lesson_id: Optional[str] = None,
    jlpt: Optional[str] = None,
    limit: int = 10
):
    """
    Generate quiz questions from ingested Japanese learning materials.
    Uses RAG to find relevant content and LLM to create questions.
    """
    try:
        session_id = str(uuid.uuid4())
        deps = AgentDependencies(session_id=session_id)
        
        query = "Japanese language quiz questions"
        if jlpt:
            query += f" JLPT {jlpt}"
        
        prompt = f"""Generate {limit} quiz questions for Japanese language learning.

Question types:
- multiple-choice: 4 options, one correct answer
- type-answer: User types Japanese answer
- match: Matching exercise
- listen: Audio-based question

For each question, provide:
- type: Question type
- question: Question in English
- questionJP: Question in Japanese (optional)
- options: Array of options (for multiple-choice/listen)
- correctAnswer: The correct answer
- explanation: Explanation of the answer

Search the knowledge base for relevant content.
Return as JSON array of question objects.

Query: {query}
JLPT filter: {jlpt or 'all'}
"""
        
        result = await rag_agent.run(prompt, deps=deps)
        
        import json
        try:
            response_text = result.output
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                questions_data = json.loads(response_text[json_start:json_end])
            else:
                questions_data = json.loads(response_text)
            
            questions = []
            for i, q_data in enumerate(questions_data[:limit]):
                question = QuizQuestion(
                    id=str(uuid.uuid4()),
                    type=q_data.get("type", "multiple-choice"),
                    question=q_data.get("question", ""),
                    questionJP=q_data.get("questionJP"),
                    options=q_data.get("options"),
                    correctAnswer=q_data.get("correctAnswer", ""),
                    explanation=q_data.get("explanation"),
                    audioUrl=q_data.get("audioUrl")
                )
                questions.append(question)
            
            return questions
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse quiz JSON: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Failed to generate quiz questions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voice/phrases", response_model=List[VoicePhrase])
async def get_voice_phrases(
    difficulty: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20
):
    """
    Generate voice practice phrases from ingested Japanese learning materials.
    Uses RAG to find phrases suitable for pronunciation practice.
    """
    try:
        session_id = str(uuid.uuid4())
        deps = AgentDependencies(session_id=session_id)
        
        query = "Japanese phrases for pronunciation practice"
        if category:
            query += f" {category}"
        
        prompt = f"""Extract {limit} Japanese phrases suitable for voice/pronunciation practice.

For each phrase, provide:
- japanese: Phrase in Japanese
- romaji: Hepburn romanization
- english: English translation
- difficulty: easy, medium, or hard
- category: Category (Greetings, Politeness, Questions, etc.)

Search the knowledge base for common Japanese phrases.
Return as JSON array of phrase objects.

Query: {query}
Difficulty filter: {difficulty or 'all'}
Category filter: {category or 'all'}
"""
        
        result = await rag_agent.run(prompt, deps=deps)
        
        import json
        try:
            response_text = result.output
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                phrases_data = json.loads(response_text[json_start:json_end])
            else:
                phrases_data = json.loads(response_text)
            
            phrases = []
            for i, p_data in enumerate(phrases_data[:limit]):
                phrase = VoicePhrase(
                    id=str(uuid.uuid4()),
                    japanese=p_data.get("japanese", ""),
                    romaji=p_data.get("romaji", ""),
                    english=p_data.get("english", ""),
                    difficulty=p_data.get("difficulty", "easy"),
                    category=p_data.get("category", "Common Phrases")
                )
                phrases.append(phrase)
            
            return phrases
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse phrases JSON: {e}")
            return []
        
    except Exception as e:
        logger.error(f"Failed to generate voice phrases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/progress/{user_id}/stats")
async def get_progress_stats(user_id: str):
    """
    Get user progress statistics including weekly data and vocabulary mastery.
    """
    try:
        # Get user progress records
        records = db_manager.get_user_progress(user_id)
        
        # Generate weekly activity data (last 7 days)
        from datetime import datetime, timedelta
        weekly_data = []
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        today = datetime.now()
        
        for i in range(7):
            day_date = today - timedelta(days=6-i)
            day_name = days[day_date.weekday()]
            
            # Calculate XP and time for this day (simplified - would need timestamp tracking)
            day_records = [r for r in records if r.get("created_at", "").startswith(day_date.strftime("%Y-%m-%d"))]
            xp = sum(r.get("xp_earned", 0) for r in day_records)
            time = len(day_records) * 5  # Estimate 5 min per activity
            
            weekly_data.append({
                "day": day_name,
                "xp": xp,
                "time": time
            })
        
        # Generate vocabulary mastery stats by JLPT level
        vocab_records = [r for r in records if r.get("type") == "vocab"]
        vocab_stats = []
        jlpt_levels = ["N5", "N4", "N3"]
        
        for level in jlpt_levels:
            level_vocab = [r for r in vocab_records if r.get("data", {}).get("jlpt") == level]
            learned = len(level_vocab)
            mastered = len([r for r in level_vocab if r.get("status") == "mastered"])
            reviewing = len([r for r in level_vocab if r.get("status") == "in_progress"])
            
            vocab_stats.append({
                "category": level,
                "learned": learned,
                "mastered": mastered,
                "reviewing": reviewing
            })
        
        return {
            "weekly": weekly_data,
            "vocab": vocab_stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get progress stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
async def text_to_speech(request: Dict[str, Any]):
    """
    Generate speech from text using Dia TTS.
    
    Request body:
        {
            "text": "Text to convert to speech"
        }
    
    Returns:
        Audio file (WAV format) as binary response
    """
    global tts_manager
    
    if tts_manager is None or not tts_manager.is_available():
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Dia TTS is not installed or failed to load."
        )
    
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Text parameter is required")
        
        logger.info(f"Generating TTS for text: {text[:50]}...")
        
        # Format Japanese text to Romaji if needed
        formatted_text = tts_manager.format_japanese_text(text)
        
        # Generate speech
        audio_array = tts_manager.generate_speech(
            formatted_text,
            max_tokens=300,  # Conservative limit for reliability
            verbose=False
        )
        
        if audio_array is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate speech. The text may be too long or TTS encountered an error."
            )
        
        # Convert numpy array to WAV bytes
        import soundfile as sf
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_array, 44100, format='WAV')
        wav_bytes = wav_buffer.getvalue()
        
        logger.info(f"Generated TTS audio: {len(wav_bytes)} bytes")
        
        # Return audio as WAV file
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav",
                "Content-Length": str(len(wav_bytes))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    
    return ErrorResponse(
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=str(uuid.uuid4())
    )


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "agent.api:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=APP_ENV == "development",
        log_level=LOG_LEVEL.lower()
    )