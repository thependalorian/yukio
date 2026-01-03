"""
Memory utilities using Mem0 for persistent conversation memory.

This module provides memory management for Yukio, enabling the tutor
to remember student progress, preferences, and learning history
across sessions.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Mem0 is optional - gracefully handle if not installed
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    Memory = None  # type: ignore

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class YukioMemory:
    """
    Memory manager for Yukio Japanese tutor.

    Provides persistent memory for:
    - Student learning progress (kanji learned, vocabulary, grammar)
    - Conversation history
    - Student preferences (difficulty level, learning style)
    - Mistakes and areas needing review
    """

    def __init__(self, user_id: Optional[str] = None):
        """
        Initialize Yukio memory manager.

        Args:
            user_id: Student identifier for personalized memory
        """
        self.user_id = user_id or os.getenv("MEM0_USER_ID", "student_default")
        self.storage_path = os.getenv("MEM0_STORAGE_PATH", "./yukio_data/mem0")
        self.memory = None
        self.is_available = False

        if not MEM0_AVAILABLE:
            logger.warning("Mem0 not installed - memory features will be disabled")
            logger.warning("Install with: pip install mem0ai")
            return

        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)

        try:
            # Initialize Mem0 with local configuration
            self.memory = Memory.from_config({
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": os.getenv("LLM_CHOICE", "qwen2.5:14b-instruct"),
                    "ollama_base_url": os.getenv("LLM_BASE_URL", "http://localhost:11434").rstrip("/v1"),
                }
            },
            "embedder": {
                "provider": "ollama",
                "config": {
                    "model": os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
                    "ollama_base_url": os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434").rstrip("/v1"),
                }
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "yukio_memory",
                    "path": self.storage_path,
                }
            },
            "version": "v1.1"
            })
            self.is_available = True
            logger.info(f"Yukio memory initialized for user: {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self.memory = None
            self.is_available = False

    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a memory entry for the current user.

        Args:
            content: Memory content to store
            metadata: Optional metadata (e.g., lesson topic, difficulty)

        Returns:
            Result of memory addition
        """
        if not self.memory:
            logger.warning("Memory not available - mem0 not installed")
            return {"error": "Memory not available"}
        try:
            result = self.memory.add(
                content,
                user_id=self.user_id,
                metadata=metadata or {}
            )
            logger.info(f"Added memory for user {self.user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            return {"error": str(e)}

    def search_memories(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user memories by query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant memories
        """
        if not self.memory:
            logger.warning("Memory not available - mem0 not installed")
            return []
        try:
            results = self.memory.search(
                query,
                user_id=self.user_id,
                limit=limit
            )
            return results.get("results", []) if isinstance(results, dict) else results
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """
        Get all memories for the current user.

        Returns:
            List of all user memories
        """
        if not self.memory:
            return []
        try:
            results = self.memory.get_all(user_id=self.user_id)
            return results.get("results", []) if isinstance(results, dict) else results
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []

    def update_memory(
        self,
        memory_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Update an existing memory.

        Args:
            memory_id: ID of memory to update
            content: New content

        Returns:
            Result of update operation
        """
        if not self.memory:
            return {"error": "Memory not available"}
        try:
            result = self.memory.update(memory_id, content)
            logger.info(f"Updated memory {memory_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to update memory: {e}")
            return {"error": str(e)}

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        if not self.memory:
            return False
        try:
            self.memory.delete(memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return False

    def clear_all_memories(self) -> bool:
        """
        Clear all memories for the current user.

        Returns:
            True if cleared successfully
        """
        if not self.memory:
            return False
        try:
            self.memory.delete_all(user_id=self.user_id)
            logger.warning(f"Cleared all memories for user {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")
            return False

    # Japanese Learning Specific Methods

    def record_kanji_learned(
        self,
        kanji: str,
        reading: str,
        meaning: str,
        example: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a kanji that the student has learned.

        Args:
            kanji: The kanji character
            reading: Reading in hiragana/katakana
            meaning: English meaning
            example: Optional example sentence

        Returns:
            Result of memory addition
        """
        content = f"Student learned kanji: {kanji} ({reading}) - {meaning}"
        if example:
            content += f". Example: {example}"

        return self.add_memory(content, metadata={
            "type": "kanji_learned",
            "kanji": kanji,
            "reading": reading,
            "meaning": meaning,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def record_vocabulary(
        self,
        word: str,
        reading: str,
        meaning: str,
        jlpt_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record vocabulary the student has learned.

        Args:
            word: Japanese word
            reading: Reading in hiragana
            meaning: English meaning
            jlpt_level: JLPT level (N5-N1)

        Returns:
            Result of memory addition
        """
        content = f"Student learned vocabulary: {word} ({reading}) - {meaning}"
        if jlpt_level:
            content += f" [JLPT {jlpt_level}]"

        return self.add_memory(content, metadata={
            "type": "vocabulary_learned",
            "word": word,
            "reading": reading,
            "meaning": meaning,
            "jlpt_level": jlpt_level,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def record_grammar_point(
        self,
        grammar: str,
        explanation: str,
        example: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a grammar point the student has studied.

        Args:
            grammar: Grammar pattern
            explanation: Brief explanation
            example: Optional example sentence

        Returns:
            Result of memory addition
        """
        content = f"Student studied grammar: {grammar} - {explanation}"
        if example:
            content += f". Example: {example}"

        return self.add_memory(content, metadata={
            "type": "grammar_learned",
            "grammar": grammar,
            "explanation": explanation,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def record_mistake(
        self,
        mistake_type: str,
        details: str,
        correction: str
    ) -> Dict[str, Any]:
        """
        Record a mistake for future review.

        Args:
            mistake_type: Type of mistake (kanji, grammar, vocabulary, etc.)
            details: What the mistake was
            correction: The correct answer

        Returns:
            Result of memory addition
        """
        content = f"Student made a {mistake_type} mistake: {details}. Correct answer: {correction}"

        return self.add_memory(content, metadata={
            "type": "mistake",
            "mistake_type": mistake_type,
            "needs_review": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def get_student_progress(self) -> Dict[str, Any]:
        """
        Get a summary of student's learning progress.

        Returns:
            Dictionary with progress statistics
        """
        all_memories = self.get_all_memories()

        progress = {
            "kanji_learned": 0,
            "vocabulary_learned": 0,
            "grammar_points": 0,
            "mistakes_to_review": 0,
            "total_memories": len(all_memories)
        }

        for memory in all_memories:
            metadata = memory.get("metadata", {})
            mem_type = metadata.get("type", "")

            if mem_type == "kanji_learned":
                progress["kanji_learned"] += 1
            elif mem_type == "vocabulary_learned":
                progress["vocabulary_learned"] += 1
            elif mem_type == "grammar_learned":
                progress["grammar_points"] += 1
            elif mem_type == "mistake" and metadata.get("needs_review"):
                progress["mistakes_to_review"] += 1

        return progress

    def get_review_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get items that need review (mistakes, difficult content).

        Args:
            limit: Maximum number of items

        Returns:
            List of items needing review
        """
        return self.search_memories("needs review mistake", limit=limit)

    def set_student_preference(
        self,
        preference_key: str,
        preference_value: str
    ) -> Dict[str, Any]:
        """
        Set a student preference.

        Args:
            preference_key: Preference name (e.g., 'difficulty_level')
            preference_value: Preference value

        Returns:
            Result of memory addition
        """
        content = f"Student preference: {preference_key} = {preference_value}"

        return self.add_memory(content, metadata={
            "type": "preference",
            "key": preference_key,
            "value": preference_value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Global memory instance (lazy initialization)
_memory_instance: Optional[YukioMemory] = None


def get_memory(user_id: Optional[str] = None) -> YukioMemory:
    """
    Get or create memory instance.

    Args:
        user_id: Optional user ID for personalization

    Returns:
        YukioMemory instance
    """
    global _memory_instance

    if _memory_instance is None or (user_id and user_id != _memory_instance.user_id):
        _memory_instance = YukioMemory(user_id)

    return _memory_instance


# Convenience functions for common operations
def remember(content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Add a memory for the current user."""
    return get_memory().add_memory(content, metadata)


def recall(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search memories for the current user."""
    return get_memory().search_memories(query, limit)


def get_progress() -> Dict[str, Any]:
    """Get student's learning progress."""
    return get_memory().get_student_progress()
