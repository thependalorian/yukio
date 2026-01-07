# Yukio - Local AI Japanese Tutor

**Yukio** is a local-first, privacy-focused AI Japanese language tutor that runs entirely on your machine. No cloud APIs, no subscriptions—just you, your computer, and a comprehensive Japanese learning experience.

Powered by a modern, local-first AI stack:
- **Ollama**: For local LLM (Qwen2.5:14b) and embeddings
- **LanceDB**: For zero-config, local vector storage (document chunks + user progress)
- **uv**: For fast, modern Python package management
- **Pydantic & FastAPI**: For a robust agent and API backend
- **Dia**: For optional, high-quality Text-to-Speech voice generation
- **Mem0**: For optional conversation memory and progress tracking

## Quick Start

### 1. Prerequisites
- **Python 3.10-3.12**: Managed with `pyenv` is recommended
- **Ollama**: Install from [ollama.ai](https://ollama.ai)
  ```bash
  # Pull the required models
  ollama pull qwen2.5:14b-instruct
  ollama pull nomic-embed-text
  ```
- **uv**: Install from [astral.sh](https://astral.sh/uv)
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Setup & Installation
From the project root, run the following to create the environment and install all dependencies:
```bash
# Create the virtual environment (uses .venv)
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Install all dependencies for the project and TTS module
uv pip install -e .[dev] -e dia
```
For a detailed setup guide, see the [**Development Setup Documentation**](./docs/development_setup.md).

### 3. Data Ingestion
Prepare the Japanese learning materials for the agent. This involves converting the provided PDFs to markdown, cleaning them, and ingesting them into the vector database.
```bash
# Run the full ingestion pipeline (converts, cleans, and ingests)
python scripts/convert_pdfs.py
python scripts/clean_markdown.py
python -m ingestion.ingest --verbose
```
For a detailed guide on the data pipeline, see the [**Ingestion Documentation**](./docs/ingestion.md).

### 4. Run the Application

#### Command-Line Interface (CLI)
Interact with Yukio through the command-line interface:
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the CLI
python cli.py

# Or run with voice enabled (see TTS docs for setup)
# ⚠️  WARNING: Voice is NOT recommended on Apple Silicon (M1/M2/M3)
# TTS generation takes 2-5 minutes per response on Mac. Use text-only mode.
python cli.py --voice
```

#### API Server (for Frontend)
Run the FastAPI server to serve the web frontend:
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the API server
python -m agent.api
# Or with uvicorn directly:
uvicorn agent.api:app --reload --port 8058
```

The API will be available at `http://localhost:8058`

> **⚠️ Apple Silicon (M1/M2/M3) Users**: Voice generation is **extremely slow** on Mac (2-5 minutes per response). We recommend using **text-only mode** (`python cli.py` without `--voice`) or enable native TTS with `export YUKIO_USE_NATIVE_TTS=1`. See [TTS documentation](./docs/tts_voice.md) for details and alternatives.

### Optional: Enable Native TTS (Apple Silicon)

For faster TTS on Apple Silicon, use the helper script:
```bash
./start_with_native_tts.sh
```

Or set the environment variable:
```bash
export YUKIO_USE_NATIVE_TTS=1
uvicorn agent.api:app --reload --port 8058
```

## API Endpoints

### Core Endpoints
- `GET /health` - Health check (LanceDB, Mem0, LLM connection status)
- `POST /chat` - Chat with Yukio (non-streaming)
- `POST /chat/stream` - Chat with Yukio (streaming SSE)
- `POST /search/vector` - Vector similarity search
- `POST /search/hybrid` - Hybrid vector + text search
- `GET /documents` - List ingested documents
- `GET /sessions/{session_id}` - Get session information

### Learning Content Endpoints (RAG-Generated)
These endpoints use the RAG agent to generate structured content from ingested materials:

- `GET /lessons` - Generate structured lessons
  - Query params: `category` (hiragana/katakana/kanji/grammar/vocabulary), `jlpt` (N5-N1), `limit`
- `GET /vocabulary` - Extract vocabulary words
  - Query params: `jlpt` (N5-N1), `limit`
- `GET /quiz/questions` - Generate quiz questions
  - Query params: `lesson_id`, `jlpt` (N5-N1), `limit`
- `GET /voice/phrases` - Extract voice practice phrases
  - Query params: `difficulty` (easy/medium/hard), `category`, `limit`

### Progress Tracking Endpoints
- `GET /progress/{user_id}` - Get user progress statistics (XP, level, streak, etc.)
- `POST /progress/{user_id}/record` - Record progress (lesson completion, vocab learned, etc.) - Returns `achievements_unlocked` array
- `GET /progress/{user_id}/lessons` - Get user's lesson/vocab progress records
- `GET /progress/{user_id}/stats` - Get progress statistics (weekly data, vocab mastery)

### Gamification & Achievements Endpoints
- `GET /achievements` - List all available achievements (28 achievements across 7 categories)
- `GET /achievements/{user_id}` - Get user's unlocked achievements with timestamps
- `GET /leaderboards/{category}` - Get leaderboard entries
  - Query params: `category` (weekly_xp, monthly_xp, all_time_xp, weekly_streak, monthly_streak, pronunciation, lessons), `period` (weekly, monthly, all-time), `limit` (default: 100)

### Career Coaching Endpoints
- `POST /career/rirekisho` - Generate Japanese resume (履歴書) or work history (職務経歴書)
  - Request body: `user_id`, `job_title` (optional), `company_name` (optional), `job_description` (optional), `document_type` (rirekisho/shokumu-keirekisho/both)
  - Returns structured sections ready for filling out rirekisho templates

## Database Architecture

Yukio uses **LanceDB** (not PostgreSQL) for local file-based storage:

### Tables
- **`japanese_lessons`** - Document chunks from ingested markdown files (for RAG search)
- **`user_progress`** - User progress tracking (lessons, vocabulary, quizzes, XP, streaks)
- **`achievements`** - Achievement definitions (28 achievements across 7 categories)
- **`user_achievements`** - User achievement unlocks with timestamps
- **`leaderboards`** - Leaderboard entries for XP, streaks, lessons, and pronunciation

### Data Storage
- **Vector embeddings**: Stored in LanceDB for semantic search
- **User progress**: Stored in LanceDB `user_progress` table
- **Conversation memory**: Optional Mem0 integration (if installed)

## Frontend Integration

The frontend (`yukio-frontend`) connects to the backend API at `http://localhost:8058`.

### Environment Variables
Set in `yukio-frontend/.env.local`:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8058
```

### Features

### 🎵 Text-to-Speech (TTS)
- **Automatic audio generation** for all responses
- **Kokoro TTS** with anime-style Japanese voices
- **Real-time text streaming** with automatic audio playback
- **Voice configuration** via environment variables
- See [TTS_AUDIO_INTEGRATION.md](./TTS_AUDIO_INTEGRATION.md) for details

## Features
- **Dashboard**: Overview of learning progress
- **Lessons**: Browse and complete structured lessons (generated from RAG data)
- **Vocabulary Practice**: Flashcard-style vocabulary learning
- **Quiz**: Interactive quizzes with multiple question types
- **Voice Practice**: Pronunciation practice with audio feedback and STT analysis
- **Chat**: AI tutor conversation interface
- **Progress**: Track XP, level, streak, and learning statistics
- **Achievements**: 28 achievements across 7 categories with automatic unlocking
- **Leaderboards**: Compete with others on XP, streaks, lessons, and pronunciation scores

All frontend features use real API endpoints - no mock data.

## 📚 Documentation

This project's documentation has been consolidated into the `/docs` directory for clarity.

- **[Development Setup](./docs/development_setup.md)**: A complete guide to setting up your local environment with `uv` and `pyenv`
- **[Ingestion Pipeline](./docs/ingestion.md)**: A detailed walkthrough of the data processing and ingestion workflow, from PDF to vector search
- **[TTS / Voice Generation](./docs/tts_voice.md)**: Instructions for setting up and using the optional Text-to-Speech features
- **[API Reference](./docs/api_reference.md)**: Complete API endpoint documentation with request/response examples
- **[STT Implementation](./STT_IMPLEMENTATION.md)**: Speech-to-Text integration with Whisper for pronunciation practice
- **[Gamification System](./GAMIFICATION_COMPLETE.md)**: Complete gamification system with achievements, leaderboards, and XP rewards

## 🗺️ Project Status

- [x] **Phase 1**: Data Preparation & Cleaning
- [x] **Phase 2**: Vector Database & Ingestion Pipeline
- [x] **Phase 3**: Core Agent Development
- [x] **Phase 4**: API Endpoints & Learning Content Generation
- [x] **Phase 5**: Frontend Integration
- [x] **Phase 6**: Progress Tracking & Gamification
- [x] **Phase 7**: Speech-to-Text (STT) & Pronunciation Analysis

## Architecture Overview

```
┌─────────────────┐
│  Frontend       │  Next.js 14 + TypeScript
│  (yukio-frontend)│  Port: 3000
└────────┬────────┘
         │ HTTP/REST
         │
┌────────▼────────┐
│  Backend API    │  FastAPI
│  (yukio/agent)  │  Port: 8058
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│LanceDB│ │ Ollama│
│Vector │ │ LLM + │
│Store  │ │Embed  │
└───────┘ └───────┘
```

## Data Sources

The system uses ingested Japanese learning materials:
- Marugoto Japanese Language and Culture series
- 250 Essential Japanese Kanji Characters
- Langenscheidt Picture Dictionary
- 700 Essential Phrases for Japanese Conversation
- List of 1000 Kanji
- And other markdown files in `data/japanese/markdown/`

All learning content (lessons, vocabulary, quizzes) is dynamically generated from these materials using RAG.

---
Built with 🏯 using a local-first, privacy-focused stack.
