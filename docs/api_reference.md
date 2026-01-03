# Yukio API Reference

Complete API reference for the Yukio backend server.

## Base URL

```
http://localhost:8058
```

## Authentication

Currently, no authentication is required. All endpoints are open. Future versions may add user authentication.

## Endpoints

### Health Check

#### `GET /health`

Check the health status of the system components.

**Response:**
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "lancedb": true,
  "memory": true,
  "llm_connection": true,
  "version": "0.1.0",
  "timestamp": "2024-01-01T00:00:00"
}
```

---

### Chat

#### `POST /chat`

Chat with Yukio AI tutor (non-streaming).

**Request:**
```json
{
  "message": "What is the difference between は and が?",
  "session_id": "optional-session-id",
  "user_id": "optional-user-id",
  "search_type": "hybrid"
}
```

**Response:**
```json
{
  "message": "The particle は (wa) marks the topic...",
  "session_id": "session-uuid",
  "sources": [...],
  "tools_used": [...],
  "metadata": {}
}
```

#### `POST /chat/stream`

Chat with Yukio AI tutor (streaming via Server-Sent Events).

**Request:** Same as `/chat`

**Response:** SSE stream with events:
- `text_delta`: Incremental text chunks
- `response`: Complete response
- `tools_used`: Tools called during generation

---

### Search

#### `POST /search/vector`

Vector similarity search across ingested materials.

**Request:**
```json
{
  "query": "hiragana basics",
  "limit": 10
}
```

**Response:**
```json
{
  "results": [
    {
      "chunk_id": "...",
      "document_id": "...",
      "content": "...",
      "score": 0.95,
      "document_title": "...",
      "document_source": "..."
    }
  ],
  "total_results": 10,
  "search_type": "vector",
  "query_time_ms": 123.45
}
```

#### `POST /search/hybrid`

Hybrid search (vector + text matching).

**Request:**
```json
{
  "query": "Japanese particles",
  "limit": 10,
  "text_weight": 0.3
}
```

**Response:** Same format as `/search/vector`

---

### Learning Content (RAG-Generated)

These endpoints use the RAG agent to dynamically generate structured content from ingested materials.

#### `GET /lessons`

Generate structured Japanese lessons.

**Query Parameters:**
- `category` (optional): Filter by category (`hiragana`, `katakana`, `kanji`, `grammar`, `vocabulary`)
- `jlpt` (optional): Filter by JLPT level (`N5`, `N4`, `N3`, `N2`, `N1`)
- `limit` (optional): Maximum number of lessons (default: 20)

**Example:**
```
GET /lessons?category=grammar&jlpt=N5&limit=10
```

**Response:**
```json
[
  {
    "id": "lesson-uuid",
    "title": "Hiragana Basics",
    "titleJP": "ひらがな基礎",
    "description": "Learn the 46 basic hiragana characters",
    "xp": 15,
    "crowns": 0,
    "status": "available",
    "jlpt": "N5",
    "category": "hiragana",
    "content": null
  }
]
```

#### `GET /vocabulary`

Extract vocabulary words from ingested materials.

**Query Parameters:**
- `jlpt` (optional): Filter by JLPT level
- `limit` (optional): Maximum number of words (default: 50)

**Response:**
```json
[
  {
    "id": "vocab-uuid",
    "japanese": "食べる",
    "reading": "たべる",
    "romaji": "taberu",
    "english": "to eat",
    "example": "ご飯を食べる",
    "exampleReading": "ごはんをたべる",
    "exampleTranslation": "to eat a meal",
    "jlpt": "N5"
  }
]
```

#### `GET /quiz/questions`

Generate quiz questions from ingested materials.

**Query Parameters:**
- `lesson_id` (optional): Filter by lesson ID
- `jlpt` (optional): Filter by JLPT level
- `limit` (optional): Maximum number of questions (default: 10)

**Response:**
```json
[
  {
    "id": "question-uuid",
    "type": "multiple-choice",
    "question": "What does 食べる mean?",
    "questionJP": "食べる",
    "options": ["to eat", "to drink", "to sleep", "to run"],
    "correctAnswer": "to eat",
    "explanation": "食べる (taberu) means 'to eat' in Japanese.",
    "audioUrl": null
  }
]
```

#### `GET /voice/phrases`

Extract voice practice phrases from ingested materials.

**Query Parameters:**
- `difficulty` (optional): Filter by difficulty (`easy`, `medium`, `hard`)
- `category` (optional): Filter by category
- `limit` (optional): Maximum number of phrases (default: 20)

**Response:**
```json
[
  {
    "id": "phrase-uuid",
    "japanese": "こんにちは",
    "romaji": "konnichiwa",
    "english": "Hello (Good afternoon)",
    "difficulty": "easy",
    "category": "Greetings"
  }
]
```

---

### Progress Tracking

#### `GET /progress/{user_id}`

Get user progress statistics.

**Response:**
```json
{
  "user_id": "user-123",
  "name": "Student",
  "level": 5,
  "xp": 1250,
  "xp_to_next_level": 500,
  "streak": 12,
  "daily_goal": 20,
  "hearts": 3,
  "jlpt_level": "N5",
  "lessons_completed": 8,
  "vocab_mastered": 45
}
```

#### `POST /progress/{user_id}/record`

Record user progress (lesson completion, vocab learned, etc.).

**Request:**
```json
{
  "progress_type": "lesson",
  "item_id": "lesson-123",
  "status": "completed",
  "data": {
    "title": "Hiragana Basics",
    "jlpt": "N5"
  },
  "xp_earned": 20,
  "crowns": 1
}
```

**Response:**
```json
{
  "id": "progress-uuid",
  "status": "recorded"
}
```

#### `GET /progress/{user_id}/lessons`

Get user's lesson/vocab progress records.

**Query Parameters:**
- `progress_type` (optional): Filter by type (`lesson`, `vocab`, `quiz`, `xp`, `streak`)

**Response:**
```json
{
  "records": [
    {
      "id": "record-uuid",
      "user_id": "user-123",
      "type": "lesson",
      "item_id": "lesson-123",
      "status": "completed",
      "data": {...},
      "xp_earned": 20,
      "crowns": 1,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

#### `GET /progress/{user_id}/stats`

Get progress statistics (weekly data, vocab mastery).

**Response:**
```json
{
  "weekly": [
    {
      "day": "Mon",
      "xp": 50,
      "time": 15
    }
  ],
  "vocab": [
    {
      "category": "N5",
      "learned": 120,
      "mastered": 95,
      "reviewing": 25
    }
  ]
}
```

---

### Documents

#### `GET /documents`

List all ingested documents.

**Query Parameters:**
- `limit` (optional): Maximum number of documents (default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Response:**
```json
{
  "documents": [
    {
      "id": "doc-uuid",
      "title": "Marugoto Japanese Language and Culture",
      "source": "marugoto_a1.md",
      "metadata": {},
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "chunk_count": 150
    }
  ],
  "total": 10,
  "limit": 20,
  "offset": 0
}
```

---

### Sessions

#### `GET /sessions/{session_id}`

Get session information.

**Response:**
```json
{
  "id": "session-uuid",
  "user_id": "user-123",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "metadata": {}
}
```

---

## Error Responses

All endpoints may return error responses in this format:

```json
{
  "error": "Error message",
  "error_type": "HTTPException",
  "details": {},
  "request_id": "uuid"
}
```

**Status Codes:**
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

---

## Rate Limiting

Currently, no rate limiting is implemented. Future versions may add rate limiting to prevent abuse.

## CORS

The API includes CORS middleware to allow requests from the frontend. By default, all origins are allowed in development.

---

## Data Generation

The learning content endpoints (`/lessons`, `/vocabulary`, `/quiz/questions`, `/voice/phrases`) use the RAG agent to:

1. **Search** the LanceDB vector database for relevant content from ingested materials
2. **Structure** the content using the LLM (Qwen2.5:14b) into the required format
3. **Return** structured JSON that the frontend can display

This means content is **dynamically generated** from your ingested materials, not pre-defined. The quality depends on:
- Quality of ingested materials
- LLM model capabilities
- RAG search relevance

---

## Database

Yukio uses **LanceDB** for local file-based storage:

- **Location**: `./yukio_data/lancedb/`
- **Tables**:
  - `japanese_lessons`: Document chunks for RAG search
  - `user_progress`: User progress tracking

No PostgreSQL or external database required!

