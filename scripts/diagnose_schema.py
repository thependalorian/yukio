#!/usr/bin/env python3
"""Diagnose LanceDB schema to fix vector search issues."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.db_utils import db_manager, initialize_database
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def diagnose():
    """Show current LanceDB schema."""
    try:
        await initialize_database()
        db_manager.create_table(embedding_dim=768)  # Ensure table exists
        
        if not db_manager._table_exists("japanese_lessons"):
            logger.warning("Table 'japanese_lessons' does not exist")
            return
        
        table = db_manager.db.open_table("japanese_lessons")
        logger.info("✅ Table 'japanese_lessons' found")
        
        # Show schema
        logger.info(f"\n📋 Schema:\n{table.schema}")
        
        # Show sample row
        try:
            sample = table.head(1).to_pandas()
            if len(sample) > 0:
                logger.info(f"\n📄 Sample row columns: {list(sample.columns)}")
                logger.info(f"\n📄 Sample data (first row):")
                for col in sample.columns:
                    value = sample[col].iloc[0]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"  {col}: {value}")
            else:
                logger.warning("Table is empty - no sample data available")
        except Exception as e:
            logger.error(f"Error reading sample: {e}")
        
        # Try a vector search to see what fields are returned
        logger.info("\n🔍 Testing vector search...")
        try:
            # Create a dummy embedding
            dummy_embedding = [0.0] * 768
            results = db_manager.vector_search(embedding=dummy_embedding, limit=1)
            if results:
                logger.info(f"\n✅ Vector search returned {len(results)} result(s)")
                logger.info(f"📄 Result fields: {list(results[0].keys())}")
                logger.info(f"📄 Sample result:")
                for key, value in results[0].items():
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"  {key}: {value}")
            else:
                logger.warning("Vector search returned no results")
        except Exception as e:
            logger.error(f"❌ Vector search failed: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(diagnose())

