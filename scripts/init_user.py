#!/usr/bin/env python3
"""
Initialize a user in LanceDB with default progress.

Usage:
    python scripts/init_user.py george_nekwaya
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.db_utils import db_manager, initialize_database
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_user(user_id: str):
    """Initialize a user in LanceDB with default progress."""
    try:
        # Initialize database
        await initialize_database()
        db_manager.create_user_progress_table()
        logger.info(f"Database initialized")
        
        # Check if user already exists
        existing_progress = db_manager.get_user_progress(user_id)
        if existing_progress:
            logger.info(f"User '{user_id}' already exists with {len(existing_progress)} progress records")
            stats = db_manager.get_user_stats(user_id)
            logger.info(f"Current stats: Level {stats['level']}, XP: {stats['xp']}, Streak: {stats['streak']}")
            return
        
        # Create initial progress record (welcome XP for complete beginner)
        logger.info(f"Initializing user '{user_id}' as a complete beginner...")
        progress_id = db_manager.record_user_progress(
            user_id=user_id,
            progress_type="xp",
            item_id="welcome",
            status="completed",
            data={
                "message": "Welcome to Yukio! You're starting your Japanese learning journey.",
                "beginner": True,
                "starting_level": "N5"
            },
            xp_earned=5,  # Small welcome bonus for beginners
            crowns=0
        )
        
        # Record beginner status
        db_manager.record_user_progress(
            user_id=user_id,
            progress_type="xp",
            item_id="beginner_setup",
            status="completed",
            data={
                "beginner": True,
                "experience_level": "complete_beginner",
                "recommended_path": "Start with Hiragana basics"
            },
            xp_earned=0,
            crowns=0
        )
        
        logger.info(f"✓ Created initial progress record: {progress_id}")
        
        # Get stats to verify
        stats = db_manager.get_user_stats(user_id)
        logger.info(f"✓ User '{user_id}' initialized successfully!")
        logger.info(f"  Name: {stats['name']}")
        logger.info(f"  Level: {stats['level']}")
        logger.info(f"  XP: {stats['xp']}")
        logger.info(f"  Streak: {stats['streak']}")
        logger.info(f"  JLPT Level: {stats['jlpt_level']}")
        
    except Exception as e:
        logger.error(f"Failed to initialize user: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/init_user.py <user_id>")
        print("Example: python scripts/init_user.py george_nekwaya")
        sys.exit(1)
    
    user_id = sys.argv[1]
    asyncio.run(init_user(user_id))

