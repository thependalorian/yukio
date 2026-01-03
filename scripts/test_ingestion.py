#!/usr/bin/env python3
"""
Test script for Yukio Japanese document ingestion.

This script verifies that the ingestion pipeline works correctly:
1. Checks Ollama is running and models are available
2. Tests embedding generation
3. Tests Japanese text chunking
4. Runs a sample ingestion

Usage:
    python scripts/test_ingestion.py
"""

import os
import sys
import asyncio
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from ingestion.embedder import create_embedder
from ingestion.chunker import ChunkingConfig, create_chunker
from agent.db_utils import db_manager

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_ollama_connection():
    """Test if Ollama is running and model is available."""
    print("\n" + "="*60)
    print("🔍 Testing Ollama Connection")
    print("="*60)
    
    try:
        embedder = create_embedder()
        
        # Try to generate a test embedding
        test_text = "こんにちは。日本語のテストです。"  # Hello. This is a Japanese test.
        test_embedding = await embedder.generate_embedding(test_text)
        
        print(f"✅ Ollama is running")
        print(f"✅ Model: {embedder.model}")
        print(f"✅ Embedding dimension: {len(test_embedding)}")
        print(f"✅ Test embedding generated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        print("\n💡 Make sure:")
        print("   1. Ollama is running: ollama serve")
        print(f"   2. Model is pulled: ollama pull {os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')}")
        return False


async def test_japanese_chunking():
    """Test Japanese text chunking."""
    print("\n" + "="*60)
    print("✂️  Testing Japanese Text Chunking")
    print("="*60)
    
    try:
        # Create chunker
        config = ChunkingConfig(
            chunk_size=200,
            chunk_overlap=50,
            use_semantic_splitting=False  # Use simple chunking for testing
        )
        chunker = create_chunker(config)
        
        # Test Japanese text
        japanese_text = """
        # 日本語の勉強
        
        こんにちは。私は日本語を勉強しています。
        毎日、漢字を練習します。
        
        今日は天気がいいです。公園に行きたいです。
        日本の文化はとても面白いです。
        """
        
        # Chunk the text
        chunks = await chunker.chunk_document(
            content=japanese_text,
            title="Japanese Study",
            source="test.md"
        )
        
        print(f"✅ Created {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            has_jp = chunk.metadata.get("has_japanese", False)
            lang = chunk.metadata.get("language", "unknown")
            print(f"\n📄 Chunk {i+1}:")
            print(f"   Length: {len(chunk.content)} chars")
            print(f"   Has Japanese: {'🇯🇵 Yes' if has_jp else '🔤 No'}")
            print(f"   Language: {lang}")
            print(f"   Content preview: {chunk.content[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Chunking test failed: {e}")
        return False


async def test_embedding_generation():
    """Test embedding generation with Japanese text."""
    print("\n" + "="*60)
    print("🔢 Testing Embedding Generation")
    print("="*60)
    
    try:
        embedder = create_embedder()
        
        # Test texts (mixed Japanese and English)
        test_texts = [
            "こんにちは",  # Hello
            "ありがとうございます",  # Thank you
            "日本語を勉強します",  # I study Japanese
            "Hello in English",
        ]
        
        # Generate embeddings
        embeddings = await embedder.generate_embeddings_batch(test_texts)
        
        print(f"✅ Generated {len(embeddings)} embeddings")
        
        for i, (text, embedding) in enumerate(zip(test_texts, embeddings)):
            print(f"\n📝 Text {i+1}: {text}")
            print(f"   Embedding dim: {len(embedding)}")
            print(f"   First 5 values: {embedding[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding test failed: {e}")
        return False


def test_lancedb_connection():
    """Test LanceDB connection and setup."""
    print("\n" + "="*60)
    print("💾 Testing LanceDB Connection")
    print("="*60)
    
    try:
        # Initialize LanceDB
        db_manager.initialize()
        
        # Get stats
        stats = db_manager.get_stats()
        
        print(f"✅ LanceDB initialized")
        print(f"✅ DB path: {stats['db_path']}")
        print(f"✅ Total chunks: {stats['total_chunks']}")
        print(f"✅ Total documents: {stats['total_documents']}")
        print(f"✅ Tables: {stats['tables']}")
        
        return True
        
    except Exception as e:
        print(f"❌ LanceDB test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("🏯 YUKIO - Ingestion System Tests")
    print("="*60)
    
    results = {
        "Ollama Connection": await test_ollama_connection(),
        "Japanese Chunking": await test_japanese_chunking(),
        "Embedding Generation": await test_embedding_generation(),
        "LanceDB Connection": test_lancedb_connection(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All tests passed! System is ready for ingestion.")
        print("\n💡 Next steps:")
        print("   1. Run: python -m ingestion.ingest")
        print("   2. Check: data/japanese/markdown for source files")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
    
    print("="*60 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
