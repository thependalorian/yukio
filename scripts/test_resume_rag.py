#!/usr/bin/env python3
"""
Test script to verify that resume information is accessible via RAG.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.db_utils import db_manager
from agent.tools import vector_search_tool, VectorSearchInput, generate_embedding

async def test_resume_rag():
    """Test that resume information can be retrieved via RAG."""
    print("🔍 Testing Resume RAG Access...\n")
    
    # Initialize database
    db_manager.initialize()
    print("✅ Database initialized\n")
    
    # Test queries
    test_queries = [
        "George Nekwaya Buffr founder",
        "MBA data analytics Brandeis",
        "AI ML Pydantic LangGraph experience",
        "fintech startup payment systems",
        "work experience professional background"
    ]
    
    print("=" * 60)
    print("TESTING RESUME SEARCH QUERIES")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: '{query}'")
        print("-" * 60)
        
        try:
            # Use vector search tool (which handles embedding generation)
            search_input = VectorSearchInput(query=query, limit=3)
            results = await vector_search_tool(search_input)
            
            if results:
                print(f"✅ Found {len(results)} results")
                for j, result in enumerate(results[:2], 1):
                    print(f"\n  Result {j}:")
                    if hasattr(result, 'document_title'):
                        print(f"    Title: {result.document_title}")
                        print(f"    Source: {result.document_source}")
                        content = result.content[:200] if result.content else ""
                        print(f"    Content: {content}...")
                        print(f"    Score: {result.score:.3f}")
                    else:
                        print(f"    {result}")
            else:
                print("❌ No results found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("TESTING SPECIFIC RESUME SECTIONS")
    print("=" * 60)
    
    # Test specific sections
    section_queries = {
        "Education": "George Nekwaya MBA Brandeis education degree",
        "Work Experience": "Buffr Inc founder CEO work experience",
        "Skills": "Python SQL machine learning AI technical skills",
        "Projects": "analytical projects machine learning peer-to-peer lending"
    }
    
    for section, query in section_queries.items():
        print(f"\n📋 {section}:")
        print(f"   Query: '{query}'")
        try:
            search_input = VectorSearchInput(query=query, limit=2)
            results = await vector_search_tool(search_input)
            if results:
                print(f"   ✅ Found relevant content")
                for result in results:
                    if hasattr(result, 'content'):
                        content_preview = result.content[:150] if result.content else ""
                        print(f"      - {content_preview}...")
                    else:
                        print(f"      - {result}")
            else:
                print(f"   ⚠️  No results")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✅ Resume RAG test completed!")
    print("\nIf you see results above, the resume data is accessible via RAG.")
    print("Yukio can now help create rirekisho documents using this information.")

if __name__ == "__main__":
    asyncio.run(test_resume_rag())

