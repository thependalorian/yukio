# Yukio API Endpoints Audit

**Date:** 2024-12-19  
**Backend Port:** 8058  
**Frontend Port:** 3000

## Summary

This document audits all API endpoints in the Yukio backend and verifies their usage in the frontend.

## Backend Endpoints (FastAPI)

### Health & Status

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| GET | `/health` | Health check for LanceDB, Memory, LLM | ✅ `api.healthCheck()` in `page.tsx` |

### Chat & Messaging

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| POST | `/chat` | Non-streaming chat | ❌ Not used (frontend uses streaming) |
| POST | `/chat/stream` | Streaming chat (SSE) | ✅ `api.chatStream()` in `chat/page.tsx` |

### Search

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| POST | `/search/vector` | Vector search | ❌ Not used in frontend |
| POST | `/search/hybrid` | Hybrid search | ❌ Not used in frontend |

### Documents & Sessions

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| GET | `/documents` | List documents | ❌ Not used in frontend |
| GET | `/sessions/{session_id}` | Get session info | ❌ Not used in frontend |

### User Progress

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| GET | `/progress/{user_id}` | Get user progress stats | ✅ `api.getUserProgress()` in `navigation.tsx`, `progress/page.tsx` |
| POST | `/progress/{user_id}/record` | Record progress event | ❌ Not used (should be called after lesson/vocab completion) |
| GET | `/progress/{user_id}/lessons` | Get user's lesson/vocab records | ❌ Not used in frontend |
| GET | `/progress/{user_id}/stats` | Get progress statistics (weekly, vocab) | ✅ `api.getProgressStats()` in `progress/page.tsx` |

### Learning Content (RAG-Generated)

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| GET | `/lessons` | Get structured lessons | ✅ `api.getLessons()` in `lessons/page.tsx` |
| GET | `/vocabulary` | Get vocabulary words | ✅ `api.getVocabulary()` in `practice/vocab/page.tsx` |
| GET | `/quiz/questions` | Get quiz questions | ✅ `api.getQuizQuestions()` in `quiz/page.tsx` |
| GET | `/voice/phrases` | Get voice practice phrases | ✅ `api.getVoicePhrases()` in `practice/voice/page.tsx` |

### Text-to-Speech

| Method | Endpoint | Description | Frontend Usage |
|--------|----------|-------------|---------------|
| POST | `/api/tts` | Generate speech from text | ✅ `AudioTutor.tsx` (line 181), `audio-button.tsx` |

## Frontend API Client Methods

All methods in `src/lib/api.ts` use `API_BASE_URL` which defaults to `http://localhost:8058`:

- ✅ `healthCheck()` → `/health`
- ✅ `chat()` → `/chat` (not used)
- ✅ `chatStream()` → `/chat/stream`
- ✅ `searchVector()` → `/search/vector` (not used)
- ✅ `searchHybrid()` → `/search/hybrid` (not used)
- ✅ `listDocuments()` → `/documents` (not used)
- ✅ `getSession()` → `/sessions/{session_id}` (not used)
- ✅ `getUserProgress()` → `/progress/{user_id}`
- ✅ `recordProgress()` → `/progress/{user_id}/record` (not used)
- ✅ `getUserLessons()` → `/progress/{user_id}/lessons` (not used)
- ✅ `getLessons()` → `/lessons`
- ✅ `getVocabulary()` → `/vocabulary`
- ✅ `getQuizQuestions()` → `/quiz/questions`
- ✅ `getVoicePhrases()` → `/voice/phrases`
- ✅ `getProgressStats()` → `/progress/{user_id}/stats`

## Issues Fixed

### 1. Hardcoded Port 8000 References
**Status:** ✅ Fixed

- `AudioTutor.tsx`:
  - Line 50: WebSocket connection → Now uses `NEXT_PUBLIC_BACKEND_URL`
  - Line 181: TTS endpoint → Now uses `NEXT_PUBLIC_BACKEND_URL`
  - Line 308: Transcribe endpoint → Now uses `NEXT_PUBLIC_BACKEND_URL`
- `ProgressDashboard.tsx`:
  - Line 36: Progress endpoint → Now uses `NEXT_PUBLIC_BACKEND_URL` and correct endpoint path

### 2. Missing TTS Endpoint
**Status:** ✅ Fixed

- Added `/api/tts` endpoint to backend (`agent/api.py`)
- Endpoint accepts `{"text": "..."}` and returns WAV audio
- Uses `TTSManager` for Dia TTS generation
- Handles Japanese text conversion to Romaji

### 3. Port Configuration
**Status:** ✅ Verified

- Backend: Port 8058 (configured in `APP_PORT`)
- Frontend: Uses `NEXT_PUBLIC_BACKEND_URL` env var (defaults to `http://localhost:8058`)
- `next.config.js`: Rewrites `/api/backend/*` to `http://localhost:8058/*`

## Environment Variables

### Backend (.env)
```bash
APP_PORT=8058
APP_HOST=0.0.0.0
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8058
```

## Endpoint Status Summary

| Category | Total | Used in Frontend | Unused |
|----------|-------|------------------|--------|
| Health | 1 | 1 | 0 |
| Chat | 2 | 1 | 1 |
| Search | 2 | 0 | 2 |
| Documents/Sessions | 2 | 0 | 2 |
| Progress | 4 | 2 | 2 |
| Learning Content | 4 | 4 | 0 |
| TTS | 1 | 1 | 0 |
| **Total** | **16** | **10** | **6** |

## Recommendations

1. **Implement Progress Recording**: Call `/progress/{user_id}/record` after lesson/vocab/quiz completion
2. **Use Session Management**: Implement `/sessions/{session_id}` for chat history
3. **Add Search UI**: Consider adding vector/hybrid search to frontend for content discovery
4. **Document Listing**: Add admin/document management UI if needed

## Testing Checklist

- [x] Health check endpoint accessible
- [x] Chat streaming works
- [x] Progress endpoints return data
- [x] Learning content endpoints generate data from RAG
- [x] TTS endpoint generates audio
- [x] All frontend API calls use correct port (8058)
- [x] No hardcoded port 8000 references remain

