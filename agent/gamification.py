"""
Gamification system for Yukio: Achievements, Badges, and Leaderboards.

This module provides:
- Achievement definitions and unlocking logic
- Badge system with rarity levels
- Leaderboard management
- Integration with progress tracking

Usage:
    from agent.gamification import GamificationService
    
    service = GamificationService()
    achievements = service.check_achievements(user_id, progress_data)
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AchievementRarity(str, Enum):
    """Achievement rarity levels."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class AchievementCategory(str, Enum):
    """Achievement categories."""
    LEARNING = "learning"
    VOCAB = "vocab"
    PRONUNCIATION = "pronunciation"
    STREAK = "streak"
    XP = "xp"
    JLPT = "jlpt"
    SPECIAL = "special"


# Achievement Definitions
ACHIEVEMENTS = [
    # Learning Milestones
    {
        "id": "first_steps",
        "name": "First Steps",
        "description": "Complete your first lesson",
        "icon": "🎯",
        "category": AchievementCategory.LEARNING,
        "rarity": AchievementRarity.BRONZE,
        "criteria": {"type": "lessons_completed", "count": 1},
        "xp_reward": 10,
    },
    {
        "id": "bookworm",
        "name": "Bookworm",
        "description": "Complete 10 lessons",
        "icon": "📚",
        "category": AchievementCategory.LEARNING,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "lessons_completed", "count": 10},
        "xp_reward": 50,
    },
    {
        "id": "scholar",
        "name": "Scholar",
        "description": "Complete 50 lessons",
        "icon": "📖",
        "category": AchievementCategory.LEARNING,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "lessons_completed", "count": 50},
        "xp_reward": 200,
    },
    {
        "id": "master_student",
        "name": "Master Student",
        "description": "Complete 100 lessons",
        "icon": "🏆",
        "category": AchievementCategory.LEARNING,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "lessons_completed", "count": 100},
        "xp_reward": 500,
    },
    
    # Vocabulary
    {
        "id": "word_collector",
        "name": "Word Collector",
        "description": "Learn 50 vocabulary words",
        "icon": "📝",
        "category": AchievementCategory.VOCAB,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "vocab_mastered", "count": 50},
        "xp_reward": 75,
    },
    {
        "id": "lexicon_master",
        "name": "Lexicon Master",
        "description": "Learn 200 vocabulary words",
        "icon": "📚",
        "category": AchievementCategory.VOCAB,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "vocab_mastered", "count": 200},
        "xp_reward": 300,
    },
    {
        "id": "vocab_expert",
        "name": "Vocabulary Expert",
        "description": "Learn 500 vocabulary words",
        "icon": "🎓",
        "category": AchievementCategory.VOCAB,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "vocab_mastered", "count": 500},
        "xp_reward": 750,
    },
    
    # Pronunciation (STT-Enabled)
    {
        "id": "first_words",
        "name": "First Words",
        "description": "Complete your first pronunciation practice",
        "icon": "🎤",
        "category": AchievementCategory.PRONUNCIATION,
        "rarity": AchievementRarity.BRONZE,
        "criteria": {"type": "pronunciation_practices", "count": 1},
        "xp_reward": 15,
    },
    {
        "id": "perfect_pronunciation",
        "name": "Perfect Pronunciation",
        "description": "Get 10 perfect scores (100%)",
        "icon": "⭐",
        "category": AchievementCategory.PRONUNCIATION,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "perfect_scores", "count": 10},
        "xp_reward": 100,
    },
    {
        "id": "pronunciation_master",
        "name": "Pronunciation Master",
        "description": "Get 50 perfect scores",
        "icon": "🎯",
        "category": AchievementCategory.PRONUNCIATION,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "perfect_scores", "count": 50},
        "xp_reward": 400,
    },
    {
        "id": "flawless_speaker",
        "name": "Flawless Speaker",
        "description": "Get 100 perfect scores",
        "icon": "🔥",
        "category": AchievementCategory.PRONUNCIATION,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "perfect_scores", "count": 100},
        "xp_reward": 1000,
    },
    {
        "id": "improver",
        "name": "Improver",
        "description": "Improve pronunciation score by 20+ points",
        "icon": "📈",
        "category": AchievementCategory.PRONUNCIATION,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "score_improvement", "points": 20},
        "xp_reward": 50,
    },
    
    # Streaks
    {
        "id": "week_warrior",
        "name": "Week Warrior",
        "description": "Maintain a 7-day streak",
        "icon": "🔥",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "streak_days", "count": 7},
        "xp_reward": 100,
    },
    {
        "id": "month_master",
        "name": "Month Master",
        "description": "Maintain a 30-day streak",
        "icon": "💪",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "streak_days", "count": 30},
        "xp_reward": 500,
    },
    {
        "id": "dedicated",
        "name": "Dedicated",
        "description": "Maintain a 100-day streak",
        "icon": "⚡",
        "category": AchievementCategory.STREAK,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "streak_days", "count": 100},
        "xp_reward": 2000,
    },
    
    # XP & Levels
    {
        "id": "rising_star",
        "name": "Rising Star",
        "description": "Reach level 5",
        "icon": "⭐",
        "category": AchievementCategory.XP,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "level", "count": 5},
        "xp_reward": 50,
    },
    {
        "id": "shining_bright",
        "name": "Shining Bright",
        "description": "Reach level 10",
        "icon": "🌟",
        "category": AchievementCategory.XP,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "level", "count": 10},
        "xp_reward": 200,
    },
    {
        "id": "superstar",
        "name": "Superstar",
        "description": "Reach level 20",
        "icon": "💫",
        "category": AchievementCategory.XP,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "level", "count": 20},
        "xp_reward": 500,
    },
    {
        "id": "legend",
        "name": "Legend",
        "description": "Reach level 50",
        "icon": "🏅",
        "category": AchievementCategory.XP,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "level", "count": 50},
        "xp_reward": 2000,
    },
    
    # JLPT Progress
    {
        "id": "n5_graduate",
        "name": "N5 Graduate",
        "description": "Complete N5 level",
        "icon": "🎌",
        "category": AchievementCategory.JLPT,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "jlpt_level", "level": "N5"},
        "xp_reward": 100,
    },
    {
        "id": "n4_achiever",
        "name": "N4 Achiever",
        "description": "Complete N4 level",
        "icon": "🎋",
        "category": AchievementCategory.JLPT,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "jlpt_level", "level": "N4"},
        "xp_reward": 300,
    },
    {
        "id": "n3_expert",
        "name": "N3 Expert",
        "description": "Complete N3 level",
        "icon": "🎍",
        "category": AchievementCategory.JLPT,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "jlpt_level", "level": "N3"},
        "xp_reward": 500,
    },
    {
        "id": "n2_master",
        "name": "N2 Master",
        "description": "Complete N2 level",
        "icon": "🎎",
        "category": AchievementCategory.JLPT,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "jlpt_level", "level": "N2"},
        "xp_reward": 1000,
    },
    {
        "id": "n1_legend",
        "name": "N1 Legend",
        "description": "Complete N1 level",
        "icon": "🏯",
        "category": AchievementCategory.JLPT,
        "rarity": AchievementRarity.PLATINUM,
        "criteria": {"type": "jlpt_level", "level": "N1"},
        "xp_reward": 2500,
    },
    
    # Special Achievements
    {
        "id": "daily_goal_crusher",
        "name": "Daily Goal Crusher",
        "description": "Complete daily goal 7 days in a row",
        "icon": "🎯",
        "category": AchievementCategory.SPECIAL,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "daily_goals", "count": 7},
        "xp_reward": 200,
    },
    {
        "id": "conversationalist",
        "name": "Conversationalist",
        "description": "Have 50 conversations with Yukio",
        "icon": "💬",
        "category": AchievementCategory.SPECIAL,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "conversations", "count": 50},
        "xp_reward": 150,
    },
    {
        "id": "quiz_master",
        "name": "Quiz Master",
        "description": "Score 100% on 10 quizzes",
        "icon": "🧠",
        "category": AchievementCategory.SPECIAL,
        "rarity": AchievementRarity.GOLD,
        "criteria": {"type": "perfect_quizzes", "count": 10},
        "xp_reward": 300,
    },
    {
        "id": "career_ready",
        "name": "Career Ready",
        "description": "Generate your first rirekisho",
        "icon": "🎨",
        "category": AchievementCategory.SPECIAL,
        "rarity": AchievementRarity.SILVER,
        "criteria": {"type": "rirekisho_generated", "count": 1},
        "xp_reward": 100,
    },
]


class GamificationService:
    """Service for managing achievements, badges, and leaderboards."""
    
    def __init__(self, db_manager=None):
        """
        Initialize gamification service.
        
        Args:
            db_manager: LanceDBManager instance for database operations
        """
        self.db_manager = db_manager
        self.achievements = {ach["id"]: ach for ach in ACHIEVEMENTS}
    
    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """
        Get all achievement definitions.
        
        Returns:
            List of achievement dictionaries with all fields
        """
        # Convert enum values to strings for JSON serialization
        achievements_list = []
        for ach in ACHIEVEMENTS:
            ach_dict = ach.copy()
            # Convert enum values to strings
            if isinstance(ach_dict.get("category"), AchievementCategory):
                ach_dict["category"] = ach_dict["category"].value
            if isinstance(ach_dict.get("rarity"), AchievementRarity):
                ach_dict["rarity"] = ach_dict["rarity"].value
            achievements_list.append(ach_dict)
        return achievements_list
    
    def get_achievement(self, achievement_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific achievement by ID."""
        return self.achievements.get(achievement_id)
    
    def check_achievements(
        self,
        user_id: str,
        progress_data: Dict[str, Any],
        user_achievements: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Check which achievements should be unlocked based on user progress.
        
        Args:
            user_id: User identifier
            progress_data: Dictionary with progress metrics:
                - lessons_completed: int
                - vocab_mastered: int
                - pronunciation_practices: int
                - perfect_scores: int
                - streak_days: int
                - level: int
                - jlpt_level: str
                - daily_goals_completed: int
                - conversations: int
                - perfect_quizzes: int
                - rirekisho_generated: int
            user_achievements: List of already unlocked achievement IDs
        
        Returns:
            List of newly unlocked achievements with metadata
        """
        if user_achievements is None:
            user_achievements = []
        
        newly_unlocked = []
        
        for achievement in ACHIEVEMENTS:
            # Skip if already unlocked
            if achievement["id"] in user_achievements:
                continue
            
            # Check if criteria are met
            criteria = achievement["criteria"]
            criteria_type = criteria.get("type")
            
            if self._check_criteria(criteria_type, criteria, progress_data):
                newly_unlocked.append({
                    "achievement": achievement,
                    "unlocked_at": datetime.now(timezone.utc).isoformat(),
                    "xp_reward": achievement["xp_reward"]
                })
                logger.info(f"Achievement unlocked: {achievement['name']} for user {user_id}")
        
        return newly_unlocked
    
    def _check_criteria(
        self,
        criteria_type: str,
        criteria: Dict[str, Any],
        progress_data: Dict[str, Any]
    ) -> bool:
        """
        Check if achievement criteria are met.
        
        Args:
            criteria_type: Type of criteria
            criteria: Criteria dictionary
            progress_data: User progress data
        
        Returns:
            True if criteria are met, False otherwise
        """
        if criteria_type == "lessons_completed":
            required = criteria.get("count", 0)
            actual = progress_data.get("lessons_completed", 0)
            return actual >= required
        
        elif criteria_type == "vocab_mastered":
            required = criteria.get("count", 0)
            actual = progress_data.get("vocab_mastered", 0)
            return actual >= required
        
        elif criteria_type == "pronunciation_practices":
            required = criteria.get("count", 0)
            actual = progress_data.get("pronunciation_practices", 0)
            return actual >= required
        
        elif criteria_type == "perfect_scores":
            required = criteria.get("count", 0)
            actual = progress_data.get("perfect_scores", 0)
            return actual >= required
        
        elif criteria_type == "score_improvement":
            required_points = criteria.get("points", 0)
            improvement = progress_data.get("score_improvement", 0)
            return improvement >= required_points
        
        elif criteria_type == "streak_days":
            required = criteria.get("count", 0)
            actual = progress_data.get("streak_days", 0)
            return actual >= required
        
        elif criteria_type == "level":
            required = criteria.get("count", 0)
            actual = progress_data.get("level", 0)
            return actual >= required
        
        elif criteria_type == "jlpt_level":
            required_level = criteria.get("level", "")
            actual_level = progress_data.get("jlpt_level", "")
            # Check if user has reached or exceeded the required JLPT level
            jlpt_order = ["N5", "N4", "N3", "N2", "N1"]
            try:
                required_idx = jlpt_order.index(required_level)
                actual_idx = jlpt_order.index(actual_level) if actual_level in jlpt_order else -1
                return actual_idx >= required_idx
            except ValueError:
                return False
        
        elif criteria_type == "daily_goals":
            required = criteria.get("count", 0)
            actual = progress_data.get("daily_goals_completed", 0)
            return actual >= required
        
        elif criteria_type == "conversations":
            required = criteria.get("count", 0)
            actual = progress_data.get("conversations", 0)
            return actual >= required
        
        elif criteria_type == "perfect_quizzes":
            required = criteria.get("count", 0)
            actual = progress_data.get("perfect_quizzes", 0)
            return actual >= required
        
        elif criteria_type == "rirekisho_generated":
            required = criteria.get("count", 0)
            actual = progress_data.get("rirekisho_generated", 0)
            return actual >= required
        
        return False
    
    def calculate_progress_data(
        self,
        user_id: str,
        progress_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate progress data from user progress records.
        
        Args:
            user_id: User identifier
            progress_records: List of progress records from database
        
        Returns:
            Dictionary with calculated progress metrics
        """
        lessons_completed = len([
            r for r in progress_records
            if r.get("type") == "lesson" and r.get("status") == "completed"
        ])
        
        vocab_mastered = len([
            r for r in progress_records
            if r.get("type") == "vocab" and r.get("status") == "mastered"
        ])
        
        # Pronunciation practices (from progress records with type "pronunciation")
        pronunciation_records = [
            r for r in progress_records
            if r.get("type") == "pronunciation"
        ]
        pronunciation_practices = len(pronunciation_records)
        
        # Perfect scores (pronunciation with score 100)
        perfect_scores = len([
            r for r in pronunciation_records
            if r.get("data", {}).get("score", 0) == 100
        ])
        
        # Streak
        streak_records = [r for r in progress_records if r.get("type") == "streak"]
        streak_days = 0
        if streak_records:
            latest_streak = max(streak_records, key=lambda x: x.get("updated_at", ""))
            streak_data = latest_streak.get("data", {})
            if isinstance(streak_data, str):
                streak_data = json.loads(streak_data)
            streak_days = streak_data.get("days", 0)
        
        # Level (calculated from XP)
        total_xp = sum(r.get("xp_earned", 0) for r in progress_records)
        level = max(1, (total_xp // 100) + 1)
        
        # JLPT level (from progress records or default)
        jlpt_level = "N5"
        jlpt_records = [r for r in progress_records if r.get("type") == "jlpt"]
        if jlpt_records:
            latest_jlpt = max(jlpt_records, key=lambda x: x.get("updated_at", ""))
            jlpt_data = latest_jlpt.get("data", {})
            if isinstance(jlpt_data, str):
                jlpt_data = json.loads(jlpt_data)
            jlpt_level = jlpt_data.get("level", "N5")
        
        # Daily goals (count consecutive days with completed goals)
        daily_goal_records = [
            r for r in progress_records
            if r.get("type") == "daily_goal" and r.get("status") == "completed"
        ]
        daily_goals_completed = len(daily_goal_records)
        
        # Conversations (count conversation records)
        conversation_records = [
            r for r in progress_records
            if r.get("type") == "conversation"
        ]
        conversations = len(conversation_records)
        
        # Perfect quizzes (quizzes with 100% score)
        quiz_records = [
            r for r in progress_records
            if r.get("type") == "quiz"
        ]
        perfect_quizzes = len([
            r for r in quiz_records
            if r.get("data", {}).get("score", 0) == 100
        ])
        
        # Rirekisho generated
        rirekisho_records = [
            r for r in progress_records
            if r.get("type") == "rirekisho"
        ]
        rirekisho_generated = len(rirekisho_records)
        
        return {
            "lessons_completed": lessons_completed,
            "vocab_mastered": vocab_mastered,
            "pronunciation_practices": pronunciation_practices,
            "perfect_scores": perfect_scores,
            "streak_days": streak_days,
            "level": level,
            "jlpt_level": jlpt_level,
            "daily_goals_completed": daily_goals_completed,
            "conversations": conversations,
            "perfect_quizzes": perfect_quizzes,
            "rirekisho_generated": rirekisho_generated,
        }

