"""
FastAPI endpoints for the Yukio Japanese Tutor.
"""

import os
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from pathlib import Path
import uuid

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import aiohttp
from dotenv import load_dotenv

from .agent import rag_agent, AgentDependencies
from .react_executor import execute_react_task

# Optional LangGraph imports
try:
    from .graph import get_agent_graph
    from .state import AgentState
    from langchain_core.messages import HumanMessage
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    get_agent_graph = None
    AgentState = None
    HumanMessage = None
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
    VoicePhrase,
    PronunciationAnalysisRequest,
    PronunciationAnalysisResponse,
    Achievement,
    UserAchievement,
    LeaderboardEntry,
    LeaderboardCategory,
    RirekishoRequest,
    RirekishoResponse,
    RirekishoSection,
    TTSRequest
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
from .stt import STTManager
from .gamification import GamificationService
from .security import validate_and_sanitize_message, detect_prompt_injection
from fastapi.responses import Response
from fastapi import UploadFile, File, Form
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

# Global STT manager (initialized in lifespan)
stt_manager: Optional[STTManager] = None

# Global gamification service
gamification_service: Optional[GamificationService] = None

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
        # Check for preferred engine from environment
        global tts_manager
        try:
            preferred_engine = os.getenv("TTS_ENGINE", "auto")  # "native", "kokoro", or "auto"
            preferred_voice = os.getenv("TTS_VOICE", "af_bella")  # Default to af_bella (less squeaky)
            speech_rate = int(os.getenv("TTS_SPEECH_RATE", "140"))  # Slower default (140 WPM)
            
            if preferred_engine == "auto":
                # Auto-select: prefer Kokoro if available (anime-style), else native
                tts_manager = TTSManager(speech_rate=speech_rate, voice=preferred_voice)
            else:
                tts_manager = TTSManager(
                    engine=preferred_engine,
                    speech_rate=speech_rate,
                    voice=preferred_voice
                )
            
            if tts_manager.is_available():
                engine_name = tts_manager.engine
                voice_info = f" (voice: {tts_manager.voice})" if tts_manager.voice else ""
                logger.info(f"TTS ({engine_name}) initialized and available{voice_info}")
            else:
                logger.info("TTS not available - voice features disabled")
        except Exception as e:
            logger.warning(f"TTS initialization failed: {e}")
            tts_manager = None
        
        # Initialize STT manager (optional, won't break if unavailable)
        global stt_manager
        try:
            whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")  # "tiny", "base", "small", "medium", "large"
            stt_manager = STTManager(model_size=whisper_model_size, language="ja")
            
            if stt_manager.is_available():
                logger.info(f"STT (Whisper {whisper_model_size}) initialized and available")
            else:
                logger.info("STT not available - pronunciation analysis disabled")
        except Exception as e:
            logger.warning(f"STT initialization failed: {e}")
            stt_manager = None
        
        # Initialize gamification service
        global gamification_service
        try:
            from .db_utils import db_manager
            gamification_service = GamificationService(db_manager=db_manager)
            logger.info("Gamification service initialized")
        except Exception as e:
            logger.warning(f"Gamification service initialization failed: {e}")
            gamification_service = None
        
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
        # Validate and sanitize user input
        sanitized_message, error = validate_and_sanitize_message(request.message)
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        # Log injection attempts (but continue processing)
        is_injection, patterns = detect_prompt_injection(request.message)
        if is_injection:
            logger.warning(f"Prompt injection attempt detected for user {request.user_id}: {patterns}")
        
        # Get or create session
        session_id = await get_or_create_session(request)
        
        # Execute agent with sanitized message
        response, tools_used = await execute_agent(
            message=sanitized_message,
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
        # Validate and sanitize user input
        sanitized_message, error = validate_and_sanitize_message(request.message)
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        # Log injection attempts (but continue processing)
        is_injection, patterns = detect_prompt_injection(request.message)
        if is_injection:
            logger.warning(f"Prompt injection attempt detected for user {request.user_id}: {patterns}")
        
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
                
                # Detect resume/career-related queries and force tool usage
                resume_keywords = ['resume', 'cv', 'rirekisho', 'shokumu-keirekisho', 'career', 'work experience', 
                                 'job application', 'work history', 'buffr', 'previous job', 'education background']
                user_message_lower = sanitized_message.lower()
                is_resume_query = any(keyword in user_message_lower for keyword in resume_keywords)
                
                # Detect complex tasks that need ReAct reasoning
                complex_task_keywords = ['create rirekisho', 'generate rirekisho', 'create shokumu', 'generate shokumu',
                                        '履歴書を作成', '職務経歴書を作成']
                needs_react = any(keyword in user_message_lower for keyword in complex_task_keywords)
                
                # Use LangGraph orchestration if enabled
                use_langgraph = os.getenv("USE_LANGGRAPH", "false").lower() == "true"
                
                if use_langgraph and LANGGRAPH_AVAILABLE:
                    try:
                        agent_graph = get_agent_graph()
                        thread = {"configurable": {"thread_id": session_id}}
                        
                        # Initialize state
                        initial_state = {
                            "user_input": sanitized_message,
                            "session_id": session_id,
                            "user_id": request.user_id,
                            "messages": [HumanMessage(content=sanitized_message)],
                            "task_type": None,
                            "needs_resume": is_resume_query,
                            "resume_data": None,
                            "agent_outcome": None,
                            "tool_calls": [],
                            "tool_results": [],
                            "validation_errors": [],
                            "needs_revision": False,
                            "metadata": {}
                        }
                        
                        # Save user message
                        await add_message(
                            session_id=session_id,
                            role="user",
                            content=sanitized_message,
                            metadata={"user_id": request.user_id}
                        )
                        
                        full_response = ""
                        node_sequence = []
                        
                        # Stream graph execution
                        async for event in agent_graph.astream(initial_state, thread, stream_mode="values"):
                            for node_name, node_state in event.items():
                                if node_name.startswith("__"):
                                    continue
                                
                                node_sequence.append(node_name)
                                
                                # Stream node progress
                                if node_name == "classify_task":
                                    task_type = node_state.get("task_type", "unknown")
                                    logger.info(f"LangGraph: Task classified as {task_type}")
                                
                                elif node_name == "load_resume":
                                    resume_count = len(node_state.get("resume_data", []))
                                    logger.info(f"LangGraph: Loaded {resume_count} resume chunks")
                                
                                elif node_name == "agent":
                                    # Stream agent response
                                    agent_outcome = node_state.get("agent_outcome", {})
                                    response = agent_outcome.get("response", "")
                                    if response:
                                        # Stream response in chunks for better UX
                                        chunk_size = 50
                                        for i in range(0, len(response), chunk_size):
                                            chunk = response[i:i + chunk_size]
                                            yield f"data: {json.dumps({'type': 'text_delta', 'text': chunk})}\n\n"
                                        full_response = response
                                    else:
                                        # If response is empty, check messages
                                        messages = node_state.get("messages", [])
                                        for msg in messages:
                                            if hasattr(msg, 'content') and msg.content:
                                                response = msg.content
                                                # Stream response in chunks
                                                chunk_size = 50
                                                for i in range(0, len(response), chunk_size):
                                                    chunk = response[i:i + chunk_size]
                                                    yield f"data: {json.dumps({'type': 'text_delta', 'text': chunk})}\n\n"
                                                full_response = response
                                                break
                                    
                                    # Stream tool calls info
                                    tool_calls = node_state.get("tool_calls", [])
                                    if tool_calls:
                                        tools_used = [tc.get("tool_name", "unknown") for tc in tool_calls]
                                        logger.info(f"LangGraph: Agent used tools: {tools_used}")
                                
                                elif node_name == "validate":
                                    errors = node_state.get("validation_errors", [])
                                    if errors:
                                        logger.warning(f"LangGraph: Validation found {len(errors)} errors")
                                
                                elif node_name == "revise":
                                    logger.info("LangGraph: Revising output based on validation")
                        
                        # Get final state if response not captured during streaming
                        if not full_response:
                            final_state = agent_graph.get_state(thread).values
                            agent_outcome = final_state.get("agent_outcome", {})
                            full_response = agent_outcome.get("response", "")
                            
                            # If still no response, check messages in final state
                            if not full_response:
                                messages = final_state.get("messages", [])
                                for msg in messages:
                                    if hasattr(msg, 'content') and msg.content:
                                        # Check if it's an AI message (not a HumanMessage)
                                        msg_type = str(type(msg))
                                        if 'AI' in msg_type or 'Assistant' in msg_type or 'AIMessage' in msg_type:
                                            full_response = msg.content
                                            # Stream the full response now since we missed it during streaming
                                            logger.info(f"LangGraph: Streaming missed response ({len(full_response)} chars)")
                                            chunk_size = 50
                                            for i in range(0, len(full_response), chunk_size):
                                                chunk = full_response[i:i + chunk_size]
                                                yield f"data: {json.dumps({'type': 'text_delta', 'text': chunk})}\n\n"
                                            break
                            elif full_response:
                                # Response found in agent_outcome but wasn't streamed - stream it now
                                logger.info(f"LangGraph: Streaming response from final state ({len(full_response)} chars)")
                                chunk_size = 50
                                for i in range(0, len(full_response), chunk_size):
                                    chunk = full_response[i:i + chunk_size]
                                    yield f"data: {json.dumps({'type': 'text_delta', 'text': chunk})}\n\n"
                        
                        logger.info(f"LangGraph: Completed workflow: {' -> '.join(node_sequence)}, response length: {len(full_response) if full_response else 0}")
                        
                        # Clean response
                        cleaned_response = clean_agent_response(full_response) if full_response else ""
                        
                        # Save response
                        await add_message(
                            session_id=session_id,
                            role="assistant",
                            content=cleaned_response,
                            metadata={
                                "user_id": request.user_id,
                                "used_langgraph": True,
                                "node_sequence": node_sequence
                            }
                        )
                        
                        # Generate and play TTS audio for the response (LangGraph path)
                        # Use global tts_manager (defined at module level)
                        global tts_manager
                        logger.debug(f"LangGraph TTS check: tts_manager={tts_manager is not None}, available={tts_manager.is_available() if tts_manager else False}, response_len={len(cleaned_response) if cleaned_response else 0}")
                        if tts_manager and tts_manager.is_available() and cleaned_response:
                            try:
                                # Extract Japanese text or use full response
                                import re
                                japanese_text = re.findall(r'[ぁ-んァ-ン一-龯]+', cleaned_response)
                                tts_text = ' '.join(japanese_text) if japanese_text else cleaned_response
                                
                                # Limit text length for TTS (avoid very long responses)
                                max_tts_length = 500
                                if len(tts_text) > max_tts_length:
                                    tts_text = tts_text[:max_tts_length] + "..."
                                
                                # Generate TTS and save to tts_output.wav
                                tts_output_path = "./yukio_data/audio/tts_output.wav"
                                logger.info(f"Generating TTS for LangGraph response (length: {len(tts_text)} chars)")
                                
                                # Generate and save (don't auto-play in API, let frontend handle playback)
                                audio = tts_manager.generate_speech(tts_text, verbose=False)
                                if audio is not None:
                                    sample_rate = 24000 if tts_manager.engine == "kokoro" else 44100
                                    tts_manager.save_audio(tts_output_path, audio, sample_rate=sample_rate)
                                    logger.info(f"TTS audio saved to: {tts_output_path}")
                                    
                                    # Send TTS ready signal to frontend with accessible URL
                                    audio_url = f"/api/audio/tts_output.wav"
                                    yield f"data: {json.dumps({'type': 'tts_ready', 'audio_path': audio_url})}\n\n"
                            except Exception as e:
                                logger.warning(f"TTS generation failed: {e}")
                        
                        yield f"data: {json.dumps({'type': 'done'})}\n\n"
                        return
                    except Exception as e:
                        logger.warning(f"LangGraph execution failed: {e}, falling back to ReAct", exc_info=True)
                        use_langgraph = False
                
                # Use ReAct executor for complex tasks
                if needs_react and not use_langgraph:
                    logger.info(f"Complex task detected, using ReAct executor: {sanitized_message}")
                    task_description = sanitized_message
                    
                    async for react_result in execute_react_task(
                        task=task_description,
                        user_message=sanitized_message,
                        session_id=session_id,
                        user_id=request.user_id,
                        stream=True
                    ):
                        # Stream ReAct results
                        if react_result.get("type") == "reasoning_step":
                            yield f"data: {json.dumps({'type': 'reasoning', 'content': react_result.get('content', '')})}\n\n"
                        elif react_result.get("type") == "validation":
                            yield f"data: {json.dumps({'type': 'validation', 'status': react_result.get('status'), 'content': react_result.get('content', '')})}\n\n"
                        elif react_result.get("type") == "intermediate":
                            yield f"data: {json.dumps({'type': 'text_delta', 'text': react_result.get('content', '')})}\n\n"
                        elif react_result.get("type") == "final_output":
                            yield f"data: {json.dumps({'type': 'text_delta', 'text': react_result.get('content', '')})}\n\n"
                            full_response = react_result.get('content', '')
                    
                    # Save assistant response
                    await add_message(
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                        metadata={"user_id": request.user_id, "used_react": True}
                    )
                    
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return
                
                # Build input with context
                full_prompt = sanitized_message
                if context:
                    context_str = "\n".join([
                        f"{msg['role']}: {msg['content']}"
                        for msg in context[-6:]
                    ])
                    full_prompt = f"Previous conversation:\n{context_str}\n\nCurrent question: {sanitized_message}"
                
                # Force tool usage for resume queries
                if is_resume_query:
                    full_prompt = f"""CRITICAL: The user is asking about their resume or career. You MUST use the get_resume() tool FIRST - this is MANDATORY.

User's question: {sanitized_message}

MANDATORY STEPS (DO NOT SKIP):
1. IMMEDIATELY call get_resume() tool - this is REQUIRED, not optional. You cannot proceed without this.
2. Wait for the tool results - the tool will return George's complete resume data
3. Use ONLY the resume information from get_resume() tool results to answer
4. Do NOT use vector_search() or hybrid_search() - use ONLY get_resume()
5. For resume reviews, respond in ENGLISH (not Japanese) for clarity
6. Do NOT ask George for information - you have it all from get_resume()

If the user asks to review the resume:
- Call get_resume() first
- Analyze the returned data
- Provide comprehensive feedback in English
- Be specific about strengths, improvements, and suggestions

{full_prompt}"""
                
                # Save user message immediately
                await add_message(
                    session_id=session_id,
                    role="user",
                    content=sanitized_message,
                    metadata={"user_id": request.user_id}
                )
                
                full_response = ""
                
                # Stream using agent.iter() pattern
                async with rag_agent.iter(full_prompt, deps=deps) as run:
                    tool_calls_detected = False
                    async for node in run:
                        # Check if this is a tool call node
                        if hasattr(rag_agent, 'is_tool_call_node') and rag_agent.is_tool_call_node(node):
                            tool_calls_detected = True
                            logger.info(f"Tool call detected: {node}")
                        elif rag_agent.is_model_request_node(node):
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
                
                # Log tool usage for debugging
                if is_resume_query:
                    logger.info(f"Resume query detected. Tools used: {[t.tool_name for t in tools_used]}")
                    if not any(t.tool_name == 'get_resume' for t in tools_used):
                        logger.warning("⚠️ Resume query but get_resume() tool was NOT called!")
                
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
                
                # Generate and play TTS audio for the response
                if tts_manager and tts_manager.is_available() and cleaned_response:
                    try:
                        # Extract Japanese text or use full response
                        import re
                        japanese_text = re.findall(r'[ぁ-んァ-ン一-龯]+', cleaned_response)
                        tts_text = ' '.join(japanese_text) if japanese_text else cleaned_response
                        
                        # Limit text length for TTS (avoid very long responses)
                        max_tts_length = 500
                        if len(tts_text) > max_tts_length:
                            tts_text = tts_text[:max_tts_length] + "..."
                        
                        # Generate TTS and save to tts_output.wav
                        tts_output_path = "./yukio_data/audio/tts_output.wav"
                        logger.info(f"Generating TTS for response (length: {len(tts_text)} chars)")
                        
                        # Generate and save (don't auto-play in API, let frontend handle playback)
                        audio = tts_manager.generate_speech(tts_text, verbose=False)
                        if audio is not None:
                            sample_rate = 24000 if tts_manager.engine == "kokoro" else 44100
                            tts_manager.save_audio(tts_output_path, audio, sample_rate=sample_rate)
                            logger.info(f"TTS audio saved to: {tts_output_path}")
                            
                            # Send TTS ready signal to frontend with accessible URL
                            audio_url = f"/api/audio/tts_output.wav"
                            yield f"data: {json.dumps({'type': 'tts_ready', 'audio_path': audio_url})}\n\n"
                    except Exception as e:
                        logger.warning(f"TTS generation failed: {e}")
                
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
        
        # Check for achievements after recording progress
        newly_unlocked = []
        if gamification_service:
            try:
                # Get user's progress records
                progress_records = db_manager.get_user_progress(user_id)
                
                # Calculate progress data
                progress_data = gamification_service.calculate_progress_data(
                    user_id, progress_records
                )
                
                # Get already unlocked achievements
                unlocked_achievements = db_manager.get_user_achievements(user_id)
                
                # Check for new achievements
                new_achievements = gamification_service.check_achievements(
                    user_id, progress_data, unlocked_achievements
                )
                
                # Unlock new achievements and award XP
                for ach_data in new_achievements:
                    achievement = ach_data["achievement"]
                    db_manager.unlock_achievement(
                        user_id,
                        achievement["id"],
                        progress={"unlocked_at": ach_data["unlocked_at"]}
                    )
                    
                    # Award XP for achievement
                    if ach_data["xp_reward"] > 0:
                        db_manager.record_user_progress(
                            user_id=user_id,
                            progress_type="achievement",
                            item_id=achievement["id"],
                            status="completed",
                            data={"achievement_name": achievement["name"]},
                            xp_earned=ach_data["xp_reward"],
                            crowns=0
                        )
                    
                    newly_unlocked.append({
                        "id": achievement["id"],
                        "name": achievement["name"],
                        "description": achievement["description"],
                        "icon": achievement["icon"],
                        "xp_reward": ach_data["xp_reward"]
                    })
                
                if newly_unlocked:
                    logger.info(f"Unlocked {len(newly_unlocked)} achievements for user {user_id}")
                    
                    # Update leaderboards when achievements are unlocked
                    try:
                        user_stats = db_manager.get_user_stats(user_id)
                        total_xp = user_stats.get("xp", 0)
                        streak = user_stats.get("streak", 0)
                        lessons = user_stats.get("lessons_completed", 0)
                        
                        # Update weekly XP leaderboard
                        now = datetime.now(timezone.utc)
                        year, week, _ = now.isocalendar()
                        period_id = f"{year}-W{week:02d}"
                        db_manager.update_leaderboard(user_id, "weekly_xp", total_xp, period_id)
                        
                        # Update monthly XP leaderboard
                        month_period = f"{now.year}-{now.month:02d}"
                        db_manager.update_leaderboard(user_id, "monthly_xp", total_xp, month_period)
                        
                        # Update all-time XP leaderboard
                        db_manager.update_leaderboard(user_id, "all_time_xp", total_xp, "all-time")
                        
                        # Update streak leaderboards
                        db_manager.update_leaderboard(user_id, "weekly_streak", streak, period_id)
                        db_manager.update_leaderboard(user_id, "monthly_streak", streak, month_period)
                        
                        # Update lessons leaderboard
                        db_manager.update_leaderboard(user_id, "lessons", lessons, "all-time")
                    except Exception as leaderboard_error:
                        logger.warning(f"Leaderboard update failed: {leaderboard_error}")
            except Exception as ach_error:
                logger.warning(f"Achievement checking failed: {ach_error}")
        
        return {
            "id": progress_id,
            "status": "recorded",
            "achievements_unlocked": newly_unlocked
        }
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


@app.post("/voice/analyze", response_model=PronunciationAnalysisResponse)
async def analyze_pronunciation(
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, M4A, etc.)"),
    target_text: str = Form(..., description="Target Japanese text"),
    target_romaji: Optional[str] = Form(None, description="Target romaji (optional)")
):
    """
    Analyze pronunciation of recorded audio.
    
    This endpoint:
    1. Transcribes the audio using Whisper STT
    2. Compares transcription with target text
    3. Calculates pronunciation score (0-100)
    4. Provides detailed feedback
    
    Args:
        audio: Audio file uploaded by user
        target_text: Target Japanese text to compare against
        target_romaji: Target romaji (optional, will be generated if not provided)
    
    Returns:
        PronunciationAnalysisResponse with transcript, score, and feedback
    """
    if not stt_manager or not stt_manager.is_available():
        raise HTTPException(
            status_code=503,
            detail="STT not available. Install Whisper: pip install openai-whisper"
        )
    
    try:
        # Save uploaded file temporarily
        import tempfile
        import shutil
        
        # Create temp file with appropriate extension
        file_ext = Path(audio.filename).suffix if audio.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_path = tmp_file.name
            # Copy uploaded file content
            shutil.copyfileobj(audio.file, tmp_file)
        
        try:
            # Analyze pronunciation
            result = stt_manager.analyze_pronunciation(
                audio_path=tmp_path,
                target_text=target_text,
                target_romaji=target_romaji
            )
            
            logger.info(f"Pronunciation analysis: {result['score']}% for '{target_text}'")
            
            # Record pronunciation practice for progress tracking
            try:
                pronunciation_data = {
                    "target_text": target_text,
                    "target_romaji": result.get("target_romaji", ""),
                    "transcript": result.get("transcript", ""),
                    "score": result.get("score", 0),
                    "feedback": result.get("feedback", "")
                }
                
                # Record as pronunciation progress
                db_manager.record_user_progress(
                    user_id="default_user",  # TODO: Get from request/auth
                    progress_type="pronunciation",
                    item_id=f"pronunciation_{uuid.uuid4().hex[:8]}",
                    status="completed",
                    data=pronunciation_data,
                    xp_earned=10 if result.get("score", 0) >= 80 else 5,  # XP based on score
                    crowns=0
                )
                
                # Check for pronunciation achievements
                newly_unlocked_achievements = []
                if gamification_service:
                    try:
                        # Use the same user_id variable defined above
                        progress_records = db_manager.get_user_progress(user_id)
                        progress_data = gamification_service.calculate_progress_data(
                            user_id, progress_records
                        )
                        unlocked_achievements = db_manager.get_user_achievements(user_id)
                        
                        new_achievements = gamification_service.check_achievements(
                            user_id, progress_data, unlocked_achievements
                        )
                        
                        # Unlock achievements and award XP
                        for ach_data in new_achievements:
                            achievement = ach_data["achievement"]
                            db_manager.unlock_achievement(
                                user_id,
                                achievement["id"],
                                progress={"unlocked_at": ach_data["unlocked_at"]}
                            )
                            
                            # Award XP for achievement
                            if ach_data["xp_reward"] > 0:
                                db_manager.record_user_progress(
                                    user_id=user_id,
                                    progress_type="achievement",
                                    item_id=achievement["id"],
                                    status="completed",
                                    data={"achievement_name": achievement["name"]},
                                    xp_earned=ach_data["xp_reward"],
                                    crowns=0
                                )
                            
                            newly_unlocked_achievements.append({
                                "id": achievement["id"],
                                "name": achievement["name"],
                                "description": achievement["description"],
                                "icon": achievement["icon"],
                                "xp_reward": ach_data["xp_reward"]
                            })
                        
                        if newly_unlocked_achievements:
                            logger.info(f"Unlocked {len(newly_unlocked_achievements)} achievements for user {user_id}")
                    except Exception as ach_error:
                        logger.warning(f"Pronunciation achievement check failed: {ach_error}")
                
                # Add achievements to response (frontend can show notifications)
                if newly_unlocked_achievements:
                    result["achievements_unlocked"] = newly_unlocked_achievements
            except Exception as progress_error:
                logger.warning(f"Failed to record pronunciation progress: {progress_error}")
            
            return PronunciationAnalysisResponse(**result)
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Pronunciation analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/achievements", response_model=List[Achievement])
async def get_all_achievements():
    """
    Get all available achievements.
    
    Returns:
        List of all achievement definitions
    """
    if not gamification_service:
        raise HTTPException(status_code=503, detail="Gamification service not available")
    
    try:
        achievements = gamification_service.get_all_achievements()
        return [Achievement(**ach) for ach in achievements]
    except Exception as e:
        logger.error(f"Failed to get achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/achievements/{user_id}", response_model=List[UserAchievement])
async def get_user_achievements_endpoint(user_id: str):
    """
    Get user's unlocked achievements.
    
    Args:
        user_id: User identifier
    
    Returns:
        List of user's achievements
    """
    try:
        unlocked_ids = db_manager.get_user_achievements(user_id)
        
        if not gamification_service:
            return []
        
        # Get achievement details
        user_achievements = []
        for ach_id in unlocked_ids:
            achievement = gamification_service.get_achievement(ach_id)
            if achievement:
                # Get unlock timestamp from database
                table = db_manager.db.open_table("user_achievements")
                entries = table.search().where(
                    f"user_id = '{user_id}' AND achievement_id = '{ach_id}'"
                ).to_list()
                
                unlocked_at = datetime.now(timezone.utc)
                if entries:
                    unlocked_at_str = entries[0].get("unlocked_at", "")
                    try:
                        unlocked_at = datetime.fromisoformat(unlocked_at_str.replace('Z', '+00:00'))
                    except:
                        pass
                
                user_achievements.append(UserAchievement(
                    id=entries[0].get("id", "") if entries else str(uuid.uuid4()),
                    user_id=user_id,
                    achievement_id=ach_id,
                    unlocked_at=unlocked_at,
                    progress=None
                ))
        
        return user_achievements
    except Exception as e:
        logger.error(f"Failed to get user achievements: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leaderboards/{category}", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    category: LeaderboardCategory,
    period: str = "weekly",
    limit: int = 100
):
    """
    Get leaderboard entries.
    
    Args:
        category: Leaderboard category
        period: Period (weekly, monthly, all-time)
        limit: Maximum number of entries
    
    Returns:
        List of leaderboard entries
    """
    try:
        # Calculate period identifier
        now = datetime.now(timezone.utc)
        
        if period == "weekly":
            # ISO week format: 2025-W03
            year, week, _ = now.isocalendar()
            period_id = f"{year}-W{week:02d}"
        elif period == "monthly":
            # Format: 2025-01
            period_id = f"{now.year}-{now.month:02d}"
        else:
            period_id = "all-time"
        
        entries = db_manager.get_leaderboard(
            category=category.value,
            period=period_id,
            limit=limit
        )
        
        # Convert to LeaderboardEntry models
        leaderboard_entries = []
        for entry in entries:
            # Get user name
            user_stats = db_manager.get_user_stats(entry.get("user_id", ""))
            leaderboard_entries.append(LeaderboardEntry(
                user_id=entry.get("user_id", ""),
                user_name=user_stats.get("name", "Anonymous"),
                score=entry.get("score", 0),
                rank=entry.get("rank", 0),
                period=period_id
            ))
        
        return leaderboard_entries
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
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


@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    """
    Serve TTS audio files to the frontend.
    
    Args:
        filename: Audio filename (e.g., tts_output.wav)
    
    Returns:
        Audio file as binary response
    """
    try:
        audio_path = Path(f"./yukio_data/audio/{filename}")
        
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail=f"Audio file not found: {filename}")
        
        # Read and return audio file
        with open(audio_path, 'rb') as f:
            audio_bytes = f.read()
        
        # Determine content type based on extension
        content_type = "audio/wav"
        if filename.endswith('.mp3'):
            content_type = "audio/mpeg"
        elif filename.endswith('.ogg'):
            content_type = "audio/ogg"
        
        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Content-Length": str(len(audio_bytes)),
                "Cache-Control": "no-cache"  # Always fetch latest audio
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve audio file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to serve audio: {str(e)}")


@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """
    Generate speech from text using macOS native TTS.
    
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
            detail="TTS service not available. macOS native TTS requires macOS."
        )
    
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text parameter is required and cannot be empty")
        
        logger.info(f"Generating TTS for text: {request.text[:50]}... (rate: {request.speech_rate} WPM)")
        
        # Generate speech (native TTS handles Japanese directly)
        # Use slower rate (160 WPM default) for clearer, more natural speech
        audio_array = tts_manager.generate_speech(
            request.text,
            verbose=False,
            speech_rate=request.speech_rate
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
        logger.error(f"TTS generation error: {e}", exc_info=True)
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


@app.post("/career/rirekisho", response_model=RirekishoResponse)
async def generate_rirekisho(request: RirekishoRequest):
    """
    Generate a Japanese resume (履歴書) or work history (職務経歴書) based on user's resume data.
    
    This endpoint:
    1. Searches the knowledge base for the user's resume information
    2. Uses the AI agent to generate appropriate Japanese resume content
    3. Returns structured sections ready for filling out rirekisho templates
    
    Request body:
        {
            "user_id": "george_nekwaya",
            "job_title": "Data Analyst" (optional),
            "company_name": "Company Name" (optional),
            "job_description": "Job description..." (optional),
            "document_type": "rirekisho" | "shokumu-keirekisho" | "both"
        }
    """
    try:
        logger.info(f"Generating {request.document_type} for user {request.user_id}")
        
        # Search for user's resume in the knowledge base using vector search tool
        from .tools import vector_search_tool, VectorSearchInput
        
        resume_query = f"George Nekwaya resume work experience education skills {request.user_id}"
        search_input = VectorSearchInput(query=resume_query, limit=10)
        resume_results = await vector_search_tool(search_input)
        
        if not resume_results:
            logger.warning(f"No resume data found for user {request.user_id}")
            # Still proceed, agent can work with general knowledge
        
        # Build context for the agent
        resume_context = "\n\n".join([
            f"**{r.document_title if hasattr(r, 'document_title') else 'Resume'}**\n{r.content if hasattr(r, 'content') else str(r)}"
            for r in resume_results[:5]
        ])
        
        # Create prompt for rirekisho generation
        job_context = ""
        if request.job_title:
            job_context += f"Target Position: {request.job_title}\n"
        if request.company_name:
            job_context += f"Target Company: {request.company_name}\n"
        if request.job_description:
            job_context += f"Job Requirements:\n{request.job_description}\n"
        
        if request.document_type == "rirekisho":
            prompt = f"""Based on the following resume information, help create a Japanese rirekisho (履歴書) document.

RESUME INFORMATION:
{resume_context}

JOB CONTEXT:
{job_context if job_context else "General job application"}

Please provide the following sections in Japanese business format (敬語):
1. 職務要約 (Job Summary) - 200-300 words describing work experience, strengths, and how you can contribute
2. 活用できる経験・知識・スキル (Experience, knowledge, and skills) - 3 bullet points
3. 職務経歴 (Work History) - Succinct summary of each job
4. 技術スキル (Technical Skills) - Computer skills, software, programming languages
5. 資格 (Qualifications) - Certifications and licenses
6. 自己PR (Self-PR) - Specific examples demonstrating skills, motivation, and enthusiasm
7. 語学力 (Language Skills) - Japanese proficiency level
8. 志望動機 (Motivation) - Why you want to work in Japan/for this company

Format your response as structured sections with clear labels."""
        
        elif request.document_type == "shokumu-keirekisho":
            prompt = f"""Based on the following resume information, help create a Japanese shokumu-keirekisho (職務経歴書) document.

RESUME INFORMATION:
{resume_context}

JOB CONTEXT:
{job_context if job_context else "General job application"}

Please provide the following sections in Japanese business format (敬語):
1. 経歴要約 (Personal History Summary) - 200-300 characters, career overview, key achievements
2. 職務内容 (Work History) - Reverse chronological order, detailed responsibilities, quantifiable results
3. 活用できる経験・知識・スキル (Qualifications, Knowledge, Skills) - Organized by category
4. 自己PR (Self-PR) - Use STAR method, connect to job requirements

Format your response as structured sections with clear labels."""
        
        else:  # both
            prompt = f"""Based on the following resume information, help create both a Japanese rirekisho (履歴書) and shokumu-keirekisho (職務経歴書).

RESUME INFORMATION:
{resume_context}

JOB CONTEXT:
{job_context if job_context else "General job application"}

Please provide sections for both documents in Japanese business format (敬語). Format your response as structured sections with clear labels."""
        
        # Use the agent to generate content
        session_id = f"rirekisho_{request.user_id}_{uuid.uuid4().hex[:8]}"
        deps = AgentDependencies(
            session_id=session_id,
            user_id=request.user_id
        )
        
        # Get agent response
        result = await rag_agent.run(prompt, deps=deps)
        
        # Parse the response - PydanticAI returns result.output (as seen in other endpoints)
        try:
            response_text = result.output
        except AttributeError:
            # Fallback if output attribute doesn't exist
            try:
                response_text = result.data
            except AttributeError:
                response_text = str(result)
        
        # Create sections (simplified - in production, you'd want more sophisticated parsing)
        sections = []
        
        # Common section patterns
        section_patterns = {
            "職務要約": ["職務要約", "Job Summary"],
            "活用できる経験・知識・スキル": ["活用できる経験", "Experience", "Skills"],
            "職務経歴": ["職務経歴", "Work History", "Work Experience"],
            "技術スキル": ["技術スキル", "Technical Skills"],
            "資格": ["資格", "Qualifications"],
            "自己PR": ["自己PR", "Self-PR", "自己紹介"],
            "語学力": ["語学力", "Language Skills"],
            "志望動機": ["志望動機", "Motivation", "志望理由"],
            "経歴要約": ["経歴要約", "Personal History Summary"],
            "職務内容": ["職務内容", "Work History Details"]
        }
        
        # Simple section extraction (can be improved)
        lines = response_text.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if this is a section header
            found_section = None
            for section_name, patterns in section_patterns.items():
                if any(pattern in line_stripped for pattern in patterns):
                    # Save previous section
                    if current_section and current_content:
                        sections.append(RirekishoSection(
                            section_name=current_section,
                            section_name_jp=current_section,
                            content="\n".join(current_content),
                            content_jp="\n".join(current_content)
                        ))
                    current_section = section_name
                    current_content = []
                    found_section = section_name
                    break
            
            if not found_section and current_section:
                current_content.append(line_stripped)
        
        # Add last section
        if current_section and current_content:
            sections.append(RirekishoSection(
                section_name=current_section,
                section_name_jp=current_section,
                content="\n".join(current_content),
                content_jp="\n".join(current_content)
            ))
        
        # If no sections found, create a single section with all content
        if not sections:
            sections.append(RirekishoSection(
                section_name="complete_document",
                section_name_jp="完全な文書",
                content=response_text,
                content_jp=response_text
            ))
        
        return RirekishoResponse(
            user_id=request.user_id,
            document_type=request.document_type,
            sections=sections,
            job_title=request.job_title,
            company_name=request.company_name
        )
        
    except Exception as e:
        logger.error(f"Failed to generate rirekisho: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate rirekisho: {str(e)}")


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "agent.api:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=APP_ENV == "development",
        log_level=LOG_LEVEL.lower()
    )