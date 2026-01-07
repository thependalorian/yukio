# Database Schema Documentation

Yukio uses **LanceDB** (local file-based vector database) instead of PostgreSQL. All data is stored locally in `./yukio_data/lancedb/`.

## Overview

LanceDB is a zero-config, local-first vector database that stores:
- **Document chunks** with embeddings for RAG (Retrieval-Augmented Generation)
- **User progress** tracking (lessons, vocabulary, XP, streaks)

## Tables

### 1. `japanese_lessons` (Main Document Chunks Table)

**Purpose**: Stores document chunks from ingested Japanese learning materials and resume data for vector search.

**Schema** (PyArrow):

```python
pa.schema([
    pa.field("id", pa.string()),                    # Unique chunk ID (UUID string)
    pa.field("document_id", pa.string()),           # Document ID (groups chunks from same document)
    pa.field("document_title", pa.string()),        # Document title (e.g., "GEORGE NEKWAYA_RESUME.md")
    pa.field("document_source", pa.string()),       # Source file name
    pa.field("content", pa.string()),              # Chunk text content
    pa.field("chunk_index", pa.int32()),          # Chunk position in document (0-based)
    pa.field("metadata", pa.string()),            # JSON string with additional metadata
    pa.field("vector", pa.list_(pa.float32(), 768)), # Embedding vector (768-dim for nomic-embed-text)
    pa.field("created_at", pa.string()),          # ISO timestamp string
])
```

**Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Unique identifier for each chunk | `"550e8400-e29b-41d4-a716-446655440000"` |
| `document_id` | string | Groups chunks from the same document | `"doc_123"` |
| `document_title` | string | Human-readable document title | `"GEORGE NEKWAYA_RESUME.md"` |
| `document_source` | string | Source file name | `"GEORGE_NEKWAYA_RESUME.md"` |
| `content` | string | The actual text content of the chunk | `"George Nekwaya is a..."` |
| `chunk_index` | int32 | Position of chunk in document | `0`, `1`, `2`, ... |
| `metadata` | string | JSON string with type-specific metadata | `'{"type": "resume_career_document", "category": "career_coaching"}'` |
| `vector` | float32[768] | Embedding vector for semantic search | `[0.123, -0.456, ...]` (768 floats) |
| `created_at` | string | ISO timestamp | `"2025-01-15T10:30:00Z"` |

**Metadata JSON Structure**:

```json
{
  "type": "japanese_learning_material" | "resume_career_document",
  "category": "career_coaching" | "grammar" | "vocabulary" | ...,
  "format": "pdf" | "markdown",
  "parser": "docling" | "ebooklib",
  "line_count": 100,
  "word_count": 500,
  "jlpt_level": "N5" | "N4" | ...,
  "language": "ja" | "en"
}
```

**Sample Data**:

```python
{
    "id": "chunk_001",
    "document_id": "resume_george_nekwaya",
    "document_title": "GEORGE NEKWAYA_RESUME.md",
    "document_source": "GEORGE_NEKWAYA_RESUME.md",
    "content": "Founder & CEO\n\nBuffr Inc. | Boston, MA, USA / Windhoek, Namibia | January 2023 - Present\n\n- Founded digital financial inclusion platform...",
    "chunk_index": 0,
    "metadata": '{"type": "resume_career_document", "category": "career_coaching"}',
    "vector": [0.123, -0.456, 0.789, ...],  # 768 dimensions
    "created_at": "2025-01-15T10:30:00Z"
}
```

**Usage**:
- Vector similarity search for RAG (Retrieval-Augmented Generation)
- Contains both Japanese learning materials AND resume data
- Used by `/search/vector` and `/search/hybrid` endpoints
- Used by chat agent to retrieve relevant context

---

### 2. `user_progress` (User Progress Tracking Table)

**Purpose**: Stores user learning progress, XP, streaks, lesson completions, and vocabulary mastery.

**Schema** (PyArrow):

```python
pa.schema([
    pa.field("id", pa.string()),              # Unique progress record ID
    pa.field("user_id", pa.string()),         # User identifier (e.g., "george_nekwaya")
    pa.field("type", pa.string()),           # Progress type: 'lesson', 'vocab', 'quiz', 'xp', 'streak'
    pa.field("item_id", pa.string()),        # Item identifier (lesson_id, vocab_id, etc.)
    pa.field("status", pa.string()),         # Status: 'completed', 'in_progress', 'locked', 'mastered'
    pa.field("data", pa.string()),           # JSON string with type-specific data
    pa.field("xp_earned", pa.int32()),       # XP points earned for this record
    pa.field("crowns", pa.int32()),          # Crowns earned (1-3)
    pa.field("created_at", pa.string()),     # ISO timestamp
    pa.field("updated_at", pa.string()),     # ISO timestamp
])
```

**Field Descriptions**:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Unique record ID | `"progress_001"` |
| `user_id` | string | User identifier | `"george_nekwaya"` |
| `type` | string | Type of progress | `"lesson"`, `"vocab"`, `"quiz"`, `"xp"`, `"streak"` |
| `item_id` | string | Item being tracked | `"lesson-123"`, `"vocab-456"` |
| `status` | string | Current status | `"completed"`, `"in_progress"`, `"locked"`, `"mastered"` |
| `data` | string | JSON string with additional data | See below |
| `xp_earned` | int32 | XP points earned | `20`, `50`, `100` |
| `crowns` | int32 | Crowns earned (1-3) | `1`, `2`, `3` |
| `created_at` | string | ISO timestamp | `"2025-01-15T10:30:00Z"` |
| `updated_at` | string | ISO timestamp | `"2025-01-15T11:00:00Z"` |

**Data JSON Structure by Type**:

**For `type: "lesson"`**:
```json
{
  "lesson_id": "lesson-123",
  "title": "Hiragana Basics",
  "category": "hiragana",
  "jlpt": "N5",
  "completed_at": "2025-01-15T10:30:00Z",
  "time_spent_seconds": 300
}
```

**For `type: "vocab"`**:
```json
{
  "vocab_id": "vocab-456",
  "japanese": "こんにちは",
  "english": "Hello",
  "mastery_level": 3,
  "last_practiced": "2025-01-15T10:30:00Z"
}
```

**For `type: "xp"`**:
```json
{
  "source": "lesson_completion",
  "amount": 20,
  "description": "Completed Hiragana Basics lesson"
}
```

**For `type: "streak"`:
```json
{
  "streak_days": 5,
  "last_activity": "2025-01-15T10:30:00Z"
}
```

**Sample Data**:

```python
{
    "id": "progress_001",
    "user_id": "george_nekwaya",
    "type": "lesson",
    "item_id": "lesson-123",
    "status": "completed",
    "data": '{"lesson_id": "lesson-123", "title": "Hiragana Basics", "category": "hiragana", "jlpt": "N5"}',
    "xp_earned": 20,
    "crowns": 1,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

**Usage**:
- Tracks user learning progress
- Used by `/progress/{user_id}` endpoint
- Used by `/progress/{user_id}/record` endpoint
- Used by `/progress/{user_id}/stats` endpoint

---

## Database Location

**Default Path**: `./yukio_data/lancedb/`

**Environment Variable**: `LANCEDB_PATH` (can override default)

**Table Names**:
- Main table: `japanese_lessons` (configurable via `LANCEDB_TABLE_NAME`)
- Progress table: `user_progress` (fixed)

## Schema Inspection

### Using Python Script

```bash
cd yukio
source .venv/bin/activate
python scripts/diagnose_schema.py
```

### Programmatically

```python
from agent.db_utils import db_manager

# Initialize
db_manager.initialize()

# Check if table exists
exists = db_manager._table_exists("japanese_lessons")

# Open table and inspect schema
table = db_manager.db.open_table("japanese_lessons")
print(table.schema)

# Get sample data
sample = table.head(5).to_pandas()
print(sample)
```

## Data Types Reference

| LanceDB Type | Python Type | Description |
|--------------|-------------|-------------|
| `pa.string()` | `str` | UTF-8 string |
| `pa.int32()` | `int` | 32-bit integer |
| `pa.float32()` | `float` | 32-bit float |
| `pa.list_(pa.float32(), 768)` | `List[float]` | Fixed-size list of 768 floats (embedding vector) |

## Indexes

LanceDB automatically creates indexes for:
- **Vector similarity search**: On `vector` field (IVF index)
- **Filter queries**: On string fields like `document_id`, `user_id`

## Query Patterns

### Vector Search
```python
# Search by embedding similarity
results = db_manager.vector_search(
    embedding=query_embedding,
    limit=10
)
```

### Filter by Document
```python
# Get all chunks from a specific document
table = db_manager.db.open_table("japanese_lessons")
results = table.search().where(f"document_id = '{document_id}'").to_list()
```

### Filter by User
```python
# Get all progress records for a user
table = db_manager.db.open_table("user_progress")
results = table.search().where(f"user_id = '{user_id}'").to_list()
```

## Migration Notes

**From PostgreSQL**: 
- The old PostgreSQL schema (`sql/schema.sql`) is no longer used
- LanceDB is file-based and doesn't require a database server
- All data is stored locally in the `yukio_data/lancedb/` directory

**Backup**:
- Simply copy the `yukio_data/lancedb/` directory to backup
- Restore by copying the directory back

## Statistics

To get table statistics:

```python
from agent.db_utils import db_manager

db_manager.initialize()
table = db_manager.db.open_table("japanese_lessons")

# Count rows (approximate)
count = table.count_rows()  # If available
# Or: len(table.head(10000).to_pandas())  # Sample count

# List all tables
tables = db_manager.db.table_names()
print(f"Tables: {tables}")
```

---

**Last Updated**: 2025-01-15
**Database System**: LanceDB (local file-based)
**Embedding Model**: nomic-embed-text (768 dimensions)

