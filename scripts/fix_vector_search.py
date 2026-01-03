#!/usr/bin/env python3
"""Fix vector search schema mismatch - diagnostic script."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.db_utils import db_manager

def diagnose():
    """Show current LanceDB schema."""
    print("🔍 Diagnosing LanceDB schema...")
    print()
    
    db_manager.initialize()
    
    try:
        table = db_manager.db.open_table("japanese_lessons")
        print("✅ Table 'japanese_lessons' found")
        print(f"\n📋 Schema:\n{table.schema}")
        
        # Show sample row
        sample = table.head(1).to_pandas()
        print(f"\n📄 Sample row columns: {list(sample.columns)}")
        if len(sample) > 0:
            print(f"\n📄 Sample data:\n{sample.to_dict('records')[0]}")
        else:
            print("\n⚠️  Table is empty - no sample data available")
        
        # Try a test search to see what fields are returned
        print("\n🔎 Testing vector search to see returned fields...")
        test_embedding = [0.0] * 768  # Dummy embedding
        results = db_manager.vector_search(test_embedding, limit=1)
        if results:
            print(f"\n✅ Search returned {len(results)} result(s)")
            print(f"📄 Result fields: {list(results[0].keys())}")
            print(f"📄 Sample result:\n{results[0]}")
        else:
            print("\n⚠️  No results returned (table may be empty)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()

