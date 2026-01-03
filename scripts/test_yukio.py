#!/usr/bin/env python3
"""
Comprehensive test script for Yukio Japanese Tutor.
Tests all components: connections, tools, voice, agent, and API.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Colors:
    """ANSI color codes."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_test(name: str):
    """Print test header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
    print(f"🧪 TEST: {name}")
    print(f"{'='*60}{Colors.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")


async def test_database_connection():
    """Test database connection and stats."""
    print_test("Database Connection")
    
    try:
        from agent.db_utils import db_manager
        
        db_manager.initialize()
        stats = db_manager.get_stats()
        
        print_success(f"Database connected: {stats['db_path']}")
        print_info(f"Total chunks: {stats['total_chunks']}")
        print_info(f"Total documents: {stats['total_documents']}")
        print_info(f"Tables: {', '.join(stats['tables'])}")
        
        return True
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False


async def test_vector_search():
    """Test vector search tool."""
    print_test("Vector Search Tool")
    
    try:
        from agent.tools import vector_search_tool, VectorSearchInput
        
        # Test with Japanese query
        query = "こんにちは"
        result = await vector_search_tool(VectorSearchInput(query=query, limit=3))
        
        print_success(f"Vector search completed: {len(result)} results")
        if result:
            print_info(f"Top result score: {result[0].score:.4f}")
            print_info(f"Top result source: {result[0].document_title}")
            print_info(f"Content preview: {result[0].content[:100]}...")
        
        return True
    except Exception as e:
        print_error(f"Vector search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hybrid_search():
    """Test hybrid search tool."""
    print_test("Hybrid Search Tool")
    
    try:
        from agent.tools import hybrid_search_tool, HybridSearchInput
        
        query = "Japanese grammar particles"
        result = await hybrid_search_tool(HybridSearchInput(query=query, limit=3))
        
        print_success(f"Hybrid search completed: {len(result)} results")
        if result:
            print_info(f"Top result score: {result[0].score:.4f}")
            print_info(f"Top result source: {result[0].document_title}")
        
        return True
    except Exception as e:
        print_error(f"Hybrid search failed: {e}")
        return False


async def test_document_tools():
    """Test document retrieval tools."""
    print_test("Document Tools")
    
    try:
        from agent.tools import list_documents_tool, DocumentListInput
        
        # List documents
        documents = await list_documents_tool(DocumentListInput(limit=5))
        
        print_success(f"Listed {len(documents)} documents")
        if documents:
            print_info(f"First document: {documents[0].title}")
            print_info(f"Chunk count: {documents[0].chunk_count}")
        
        return True
    except Exception as e:
        print_error(f"Document tools failed: {e}")
        return False


async def test_memory_tools():
    """Test memory/search tools."""
    print_test("Memory Tools")
    
    try:
        from agent.tools import memory_search_tool, MemorySearchInput
        
        # Test memory search
        result = await memory_search_tool(MemorySearchInput(query="kanji", limit=5))
        
        print_success(f"Memory search completed: {len(result)} results")
        print_info("Memory system is functional")
        
        return True
    except Exception as e:
        print_error(f"Memory tools failed: {e}")
        return False


async def test_agent_initialization():
    """Test agent initialization."""
    print_test("AI Agent Initialization")
    
    try:
        from agent.agent import rag_agent
        
        print_success("Agent initialized successfully")
        print_info(f"Agent type: {type(rag_agent).__name__}")
        
        # Check if agent has tools
        if hasattr(rag_agent, '_tools'):
            tool_count = len(rag_agent._tools) if rag_agent._tools else 0
            print_info(f"Agent has {tool_count} tools registered")
        
        return True
    except Exception as e:
        print_error(f"Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_query():
    """Test agent with a simple query."""
    print_test("Agent Query Test")
    
    try:
        from agent.agent import rag_agent, AgentDependencies
        
        # Simple test query
        query = "What is こんにちは?"
        deps = AgentDependencies(session_id="test_session", user_id="test_user")
        
        print_info(f"Query: {query}")
        print_info("Running agent (this may take a moment)...")
        
        result = await rag_agent.run(query, deps=deps)
        
        print_success("Agent query completed")
        # Get response data - PydanticAI uses result.data for the response
        if hasattr(result, 'data'):
            response_text = result.data
        elif hasattr(result, 'output'):
            response_text = result.output
        else:
            response_text = str(result)
        
        print_info(f"Response length: {len(response_text)} characters")
        print_info(f"Response preview: {response_text[:200]}...")
        
        return True
    except Exception as e:
        print_error(f"Agent query failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tts_availability():
    """Test TTS availability."""
    print_test("Text-to-Speech (TTS)")
    
    try:
        from agent.tts import TTSManager
        
        tts = TTSManager()
        
        if tts.is_available():
            print_success("TTS is available")
            print_info(f"Model loaded: {tts.is_loaded}")
            print_info(f"Device: {tts.device}")
            return True
        else:
            print_info("TTS is not available (Dia not installed or configured)")
            print_info("This is optional - Yukio works without TTS")
            return True  # Not a failure, just optional
    except Exception as e:
        print_info(f"TTS check: {e}")
        print_info("TTS is optional - Yukio works without it")
        return True  # Not a failure


async def test_session_management():
    """Test session management."""
    print_test("Session Management")
    
    try:
        from agent.db_utils import create_session, get_session, add_message, get_session_messages
        
        # Create session
        session_id = await create_session(user_id="test_user", metadata={"test": True})
        print_success(f"Session created: {session_id[:8]}...")
        
        # Get session
        session = await get_session(session_id)
        if session:
            print_success("Session retrieved successfully")
            print_info(f"User ID: {session.get('user_id')}")
        
        # Add message
        await add_message(session_id, "user", "Test message", {"test": True})
        print_success("Message added")
        
        # Get messages
        messages = await get_session_messages(session_id, limit=10)
        print_success(f"Retrieved {len(messages)} messages")
        
        return True
    except Exception as e:
        print_error(f"Session management failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_import():
    """Test API module import."""
    print_test("FastAPI Module")
    
    try:
        from agent.api import app
        
        print_success("FastAPI app imported successfully")
        print_info(f"App title: {app.title}")
        print_info(f"App version: {app.version}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        print_info(f"Available routes: {len(routes)}")
        print_info(f"Sample routes: {', '.join(routes[:5])}")
        
        return True
    except Exception as e:
        print_error(f"API import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_embedding_generation():
    """Test embedding generation."""
    print_test("Embedding Generation")
    
    try:
        from ingestion.embedder import create_embedder
        
        embedder = create_embedder()
        test_text = "こんにちは。日本語のテストです。"
        
        embedding = await embedder.generate_embedding(test_text)
        
        print_success(f"Embedding generated: {len(embedding)} dimensions")
        print_info(f"Model: {embedder.model}")
        print_info(f"First few values: {embedding[:5]}")
        
        return True
    except Exception as e:
        print_error(f"Embedding generation failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print("🏯 YUKIO COMPREHENSIVE TEST SUITE")
    print(f"{'='*60}{Colors.END}\n")
    
    tests = [
        ("Database Connection", test_database_connection()),
        ("Embedding Generation", test_embedding_generation()),
        ("Vector Search", test_vector_search()),
        ("Hybrid Search", test_hybrid_search()),
        ("Document Tools", test_document_tools()),
        ("Memory Tools", test_memory_tools()),
        ("Session Management", test_session_management()),
        ("Agent Initialization", test_agent_initialization()),
        ("Agent Query", test_agent_query()),
        ("TTS Availability", test_tts_availability()),
        ("API Import", test_api_import()),
    ]
    
    results = []
    
    for name, test_coro in tests:
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((name, result))
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}{Colors.END}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed ({passed/total*100:.1f}%){Colors.END}\n")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

