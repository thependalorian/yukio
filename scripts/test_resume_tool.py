#!/usr/bin/env python3
"""
Test the get_resume tool to verify resume is accessible.
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.db_utils import db_manager
from agent.tools import vector_search_tool, VectorSearchInput

async def test_resume_access():
    """Test that resume is accessible via search."""
    print("🔍 Testing Resume Access in Database...\n")
    
    db_manager.initialize()
    
    # Test queries that should find resume
    queries = [
        "George Nekwaya resume",
        "Buffr founder CEO",
        "MBA Brandeis work experience"
    ]
    
    for query in queries:
        print(f"📝 Query: '{query}'")
        try:
            result = await vector_search_tool(VectorSearchInput(query=query, limit=5))
            
            # Filter for resume
            resume_results = [
                r for r in result 
                if "GEORGE" in r.document_title.upper() or 
                   "RESUME" in r.document_title.upper()
            ]
            
            if resume_results:
                print(f"   ✅ Found {len(resume_results)} resume chunks")
                for r in resume_results[:2]:
                    print(f"      - {r.document_title}")
                    print(f"        Content preview: {r.content[:100]}...")
            else:
                print(f"   ⚠️  No resume-specific results (found {len(result)} total results)")
                if result:
                    print(f"      Top result: {result[0].document_title}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
    
    print("=" * 60)
    print("✅ Resume access test complete!")
    print("\nIf you see resume chunks above, the resume is accessible.")
    print("Yukio should be able to use get_resume() tool to access it.")

if __name__ == "__main__":
    asyncio.run(test_resume_access())

