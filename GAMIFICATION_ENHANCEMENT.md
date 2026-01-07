# Gamification Enhancement Plan for Yukio

## Overview

Based on competitive analysis and gamification best practices, this document outlines the enhanced gamification system for Yukio, including achievements, badges, and leaderboards.

## Current State

✅ **Already Implemented**:
- XP (Experience Points) system
- Level progression (1-10+)
- Streak tracking
- Hearts system (3 lives in quizzes)
- Crown rewards for lesson completion
- JLPT level tracking (N5-N1)
- Daily goals
- Weekly activity charts
- Vocabulary mastery tracking

❌ **Missing** (Identified in Competitive Analysis):
- Achievements/Badges system
- Leaderboards
- Social competition
- Achievement notifications

## Enhancement Plan

### 1. Achievements & Badges System

#### Achievement Categories

**Learning Milestones**:
- 🎯 **First Steps**: Complete first lesson
- 📚 **Bookworm**: Complete 10 lessons
- 📖 **Scholar**: Complete 50 lessons
- 🏆 **Master Student**: Complete 100 lessons

**Vocabulary**:
- 📝 **Word Collector**: Learn 50 vocabulary words
- 📚 **Lexicon Master**: Learn 200 vocabulary words
- 🎓 **Vocabulary Expert**: Learn 500 vocabulary words

**Pronunciation (STT-Enabled)**:
- 🎤 **First Words**: Complete first pronunciation practice
- ⭐ **Perfect Pronunciation**: Get 10 perfect scores (100%)
- 🎯 **Pronunciation Master**: Get 50 perfect scores
- 🔥 **Flawless Speaker**: Get 100 perfect scores
- 📈 **Improver**: Improve pronunciation score by 20+ points

**Streaks**:
- 🔥 **Week Warrior**: 7-day streak
- 💪 **Month Master**: 30-day streak
- ⚡ **Dedicated**: 100-day streak

**XP & Levels**:
- ⭐ **Rising Star**: Reach level 5
- 🌟 **Shining Bright**: Reach level 10
- 💫 **Superstar**: Reach level 20
- 🏅 **Legend**: Reach level 50

**JLPT Progress**:
- 🎌 **N5 Graduate**: Complete N5 level
- 🎋 **N4 Achiever**: Complete N4 level
- 🎍 **N3 Expert**: Complete N3 level
- 🎎 **N2 Master**: Complete N2 level
- 🏯 **N1 Legend**: Complete N1 level

**Special Achievements**:
- 🎯 **Daily Goal Crusher**: Complete daily goal 7 days in a row
- 💬 **Conversationalist**: Have 50 conversations with Yukio
- 🧠 **Quiz Master**: Score 100% on 10 quizzes
- 🎨 **Career Ready**: Generate first rirekisho

#### Achievement Data Model

```python
class Achievement(BaseModel):
    id: str
    name: str
    description: str
    icon: str  # Emoji or icon identifier
    category: Literal["learning", "vocab", "pronunciation", "streak", "xp", "jlpt", "special"]
    criteria: Dict[str, Any]  # Achievement criteria (e.g., {"type": "lessons_completed", "count": 10})
    xp_reward: int
    unlocked_at: Optional[datetime] = None
```

#### Achievement Unlocking Logic

Achievements are checked automatically when:
- User completes a lesson
- User masters vocabulary
- User completes pronunciation practice
- User's streak updates
- User levels up
- User reaches JLPT milestones

### 2. Leaderboards System

#### Leaderboard Categories

**Weekly Leaderboards** (reset every Monday):
- 📊 **XP Leaderboard**: Top users by weekly XP
- 🔥 **Streak Leaderboard**: Longest current streaks
- 🎯 **Pronunciation Leaderboard**: Highest average pronunciation scores
- 📚 **Lessons Leaderboard**: Most lessons completed

**Monthly Leaderboards** (reset first of month):
- 🏆 **Overall XP**: Total XP earned
- 📈 **Most Improved**: Biggest XP gain
- 🎤 **Pronunciation Champion**: Best average pronunciation

**All-Time Leaderboards**:
- 👑 **Hall of Fame**: Top 100 users by total XP
- 🌟 **Streak Legends**: Longest streaks ever achieved

#### Privacy & Participation

- **Opt-in**: Users can choose to participate in leaderboards
- **Anonymous Mode**: Show as "Anonymous User #123" if preferred
- **Friend Leaderboards**: Optional friend-only leaderboards (future)

### 3. Badge Display System

#### Badge Rarity Levels

- 🥉 **Bronze**: Common achievements (e.g., first lesson)
- 🥈 **Silver**: Uncommon achievements (e.g., 10 perfect pronunciations)
- 🥇 **Gold**: Rare achievements (e.g., 100-day streak)
- 💎 **Platinum**: Legendary achievements (e.g., N1 completion)

#### Badge Collection View

- Grid display of all achievements
- Locked achievements shown with gray overlay
- Unlocked achievements with animation on unlock
- Progress indicators for multi-step achievements

### 4. Integration Points

#### Backend Integration

1. **Achievement Service** (`agent/gamification.py`):
   - Achievement definitions
   - Unlocking logic
   - Progress tracking

2. **Database Schema**:
   - `achievements` table: Achievement definitions
   - `user_achievements` table: User achievement unlocks
   - `leaderboards` table: Leaderboard entries

3. **API Endpoints**:
   - `GET /achievements`: List all achievements
   - `GET /achievements/{user_id}`: User's achievements
   - `POST /achievements/unlock`: Unlock achievement (internal)
   - `GET /leaderboards/{category}`: Get leaderboard
   - `POST /leaderboards/opt-in`: Opt into leaderboards

#### Frontend Integration

1. **Achievements Page** (`/achievements`):
   - Grid of all achievements
   - Filter by category
   - Progress indicators
   - Unlock animations

2. **Leaderboards Page** (`/leaderboards`):
   - Category tabs
   - User's position highlighted
   - Weekly/monthly/all-time views

3. **Achievement Notifications**:
   - Toast notifications on unlock
   - Achievement popup modal
   - Sound effect (optional)

### 5. STT-Specific Achievements

Since we just added STT, these achievements leverage the new pronunciation practice:

- **First Pronunciation**: Complete first voice practice
- **Perfect Score**: Get 100% on pronunciation
- **Perfect 10**: Get 10 perfect scores
- **Perfect 50**: Get 50 perfect scores
- **Improver**: Improve score by 20+ points
- **Consistent**: Get 80+ score 10 times in a row
- **Pronunciation Master**: Average 90+ over 50 practices

### 6. Implementation Priority

**Phase 1 (Immediate)**:
1. Achievement definitions and data models
2. Achievement unlocking logic
3. Basic achievement tracking
4. Achievement display in progress page

**Phase 2 (Next)**:
1. Leaderboard system
2. Leaderboard API endpoints
3. Leaderboard UI

**Phase 3 (Future)**:
1. Social features (friend leaderboards)
2. Achievement sharing
3. Badge customization
4. Achievement challenges

## Database Schema

### Achievements Table

```python
achievements = pa.schema([
    pa.field("id", pa.string()),
    pa.field("name", pa.string()),
    pa.field("description", pa.string()),
    pa.field("icon", pa.string()),
    pa.field("category", pa.string()),
    pa.field("criteria", pa.string()),  # JSON string
    pa.field("xp_reward", pa.int32()),
    pa.field("rarity", pa.string()),  # bronze, silver, gold, platinum
    pa.field("created_at", pa.string()),
])
```

### User Achievements Table

```python
user_achievements = pa.schema([
    pa.field("id", pa.string()),
    pa.field("user_id", pa.string()),
    pa.field("achievement_id", pa.string()),
    pa.field("unlocked_at", pa.string()),
    pa.field("progress", pa.string()),  # JSON string for progress tracking
])
```

### Leaderboards Table

```python
leaderboards = pa.schema([
    pa.field("id", pa.string()),
    pa.field("user_id", pa.string()),
    pa.field("category", pa.string()),  # weekly_xp, monthly_xp, etc.
    pa.field("score", pa.int64()),
    pa.field("period", pa.string()),  # 2025-W03, 2025-01, all-time
    pa.field("rank", pa.int32()),
    pa.field("updated_at", pa.string()),
])
```

## API Endpoints

### Achievements

- `GET /achievements` - List all achievements
- `GET /achievements/{user_id}` - Get user's achievements
- `GET /achievements/{user_id}/recent` - Recent unlocks

### Leaderboards

- `GET /leaderboards/{category}` - Get leaderboard
  - Query params: `period` (weekly, monthly, all-time), `limit` (default: 100)
- `GET /leaderboards/{category}/user/{user_id}` - Get user's position
- `POST /leaderboards/opt-in` - Opt into leaderboards
- `POST /leaderboards/opt-out` - Opt out of leaderboards

## Frontend Components

### Achievement Components

- `AchievementCard.tsx` - Individual achievement display
- `AchievementGrid.tsx` - Grid of achievements
- `AchievementModal.tsx` - Achievement unlock popup
- `AchievementProgress.tsx` - Progress indicator

### Leaderboard Components

- `LeaderboardTable.tsx` - Leaderboard display
- `LeaderboardCategoryTabs.tsx` - Category selection
- `LeaderboardEntry.tsx` - Individual entry

## Next Steps

1. ✅ Create achievement definitions
2. ✅ Implement achievement unlocking logic
3. ✅ Add achievement tracking to progress system
4. ✅ Create leaderboard system
5. ✅ Build frontend components
6. ✅ Add achievement notifications
7. ✅ Integrate with STT pronunciation practice

---

**Status**: Planning Complete  
**Next**: Implementation  
**Version**: 1.0

