#!/usr/bin/env python3
"""
Quick script to ingest George's resume into LanceDB.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.ingest import DocumentIngestionPipeline, JapaneseIngestionConfig

async def main():
    """Ingest the resume markdown file."""
    print("🏯 Ingesting George Nekwaya Resume into LanceDB...\n")
    
    # Create config
    config = JapaneseIngestionConfig(
        chunk_size=800,
        chunk_overlap=150,
        max_chunk_size=1500,
        use_semantic_chunking=True
    )
    
    # Create pipeline
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder="data/japanese/markdown",
        clean_before_ingest=False
    )
    
    # Initialize
    await pipeline.initialize()
    
    # Ingest documents (will process all markdown files including resume)
    def progress_callback(current: int, total: int):
        pct = (current / total) * 100
        print(f"📊 Progress: {current}/{total} ({pct:.1f}%)")
    
    try:
        results = await pipeline.ingest_documents(progress_callback)
        
        print("\n" + "="*60)
        print("✅ INGESTION COMPLETE")
        print("="*60)
        
        # Results is a list of document info
        if isinstance(results, list):
            print(f"📄 Documents processed: {len(results)}")
            for doc_info in results:
                if isinstance(doc_info, dict):
                    print(f"  - {doc_info.get('title', 'Unknown')}: {doc_info.get('chunks', 0)} chunks")
                else:
                    print(f"  - {doc_info}")
        else:
            print(f"📄 Results: {results}")
        
        print("="*60)
        
        # Check if resume was processed by searching the database
        try:
            from agent.db_utils import db_manager
            db_manager.initialize()
            # Search for resume content
            search_results = db_manager.vector_search(
                query="George Nekwaya Buffr founder resume",
                limit=5
            )
            if search_results:
                print("\n✅ Resume content found in database!")
                print(f"   Found {len(search_results)} relevant chunks")
            else:
                print("\n⚠️  Resume content not found in search. May need to verify ingestion.")
        except Exception as e:
            print(f"\n⚠️  Could not verify resume in database: {e}")
            
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

