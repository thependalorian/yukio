# Yukio Ingestion Pipeline: From PDF to Vector Search

This guide provides a comprehensive overview of the Yukio document ingestion pipeline, which processes Japanese learning materials, cleans them, and stores them in a local LanceDB vector database for the AI tutor to use.

## 1. Ingestion Workflow Overview

The pipeline is a 6-step process designed to ensure high-quality data for the RAG (Retrieval-Augmented Generation) system.

**Old Workflow ❌**
```
PDF → Markdown → Encoding Fix → Ingest
                                  ↓
                            Poor quality vectors
```

**New, Improved Workflow ✅**
```
PDF → Markdown → Encoding Fix → ✨ Clean OCR Garbage → Verify Setup → Ingest
                                                                      ↓
                                                            High quality vectors!
```

## 2. The Complete 6-Step Workflow

### Step 1: Convert PDFs to Markdown
- **Script**: `scripts/convert_pdfs.py`
- **Action**: Converts all PDF files in `data/japanese/` into markdown files in `data/japanese/markdown/`.
- **Command**: `python scripts/convert_pdfs.py`

### Step 2: Fix Japanese Encoding
- **Script**: `scripts/fix_encoding.py`
- **Action**: Ensures all markdown files are correctly encoded in UTF-8 to handle Japanese characters properly.
- **Command**: `python scripts/fix_encoding.py`

### Step 3: Clean Markdown (Crucial Step!)
- **Script**: `scripts/clean_markdown.py`
- **Action**: Removes OCR errors, image placeholders, and other "garbage" left over from PDF conversion. This step is **mandatory for high-quality results**.
- **Why?**: PDF conversion creates thousands of useless lines. Cleaning removes ~26% of the file size, which is pure garbage, improving data quality by over 50%.
- **Commands**:
  ```bash
  # 1. See what will be removed (safe, no changes made)
  python scripts/clean_markdown.py --dry-run

  # 2. If the dry run looks good, perform the cleaning
  python scripts/clean_markdown.py
  ```
- **Safety**: The script automatically creates `.md.backup` files so you can easily revert any changes.

### Step 4: Verify Setup
- **Script**: `scripts/quick_test.sh`
- **Action**: A quick bash script to verify that Ollama is running, the required models are available, and the markdown files exist.
- **Command**: `./scripts/quick_test.sh`

### Step 5: Run Ingestion
- **Script**: `python -m ingestion.ingest`
- **Action**: This is the main event. The script reads the cleaned markdown files, chunks them intelligently, generates embeddings via Ollama, and stores them in LanceDB.
- **Commands**:
  ```bash
  # Basic ingestion
  python -m ingestion.ingest

  # Recommended: with verbose logging
  python -m ingestion.ingest --verbose

  # To start fresh, deleting old data
  python -m ingestion.ingest --clean --verbose
  ```

### Step 6: Verify Ingestion Results
- **Action**: Check the LanceDB statistics to confirm the data has been ingested.
- **Command**:
  ```python
  python -c "from agent.db_utils import db_manager; db_manager.initialize(); print(db_manager.get_stats())"
  ```
- **Expected Output**: `{'total_chunks': 487, 'total_documents': 5, ...}` (numbers may vary)

---

## 3. Technical Details of the Pipeline

### Japanese-Aware Chunking (with spaCy)

The chunking process is optimized for the Japanese language.

- **Before**: The system used simple regex to split sentences. This was fast but often cut sentences in half.
- **After**: The chunker now uses **spaCy** and the `ja_core_news_lg` model for linguistically-aware sentence segmentation.

**How it Works:**
1.  The `ingestion/chunker.py` automatically detects if Japanese text is present.
2.  If spaCy and the Japanese model are installed, it uses them to accurately identify sentence boundaries (respecting `。`, `！`, `？`).
3.  If spaCy is not available, it **automatically falls back** to the old regex method, ensuring the pipeline never breaks.
4.  This process results in clean, semantically coherent chunks, which is critical for high-quality embeddings.

### Ollama Embedding Generation

- **Module**: `ingestion/embedder.py`
- **Models**: Supports `nomic-embed-text` (default, 768 dimensions), `bge-m3` (1024 dimensions), and `mxbai-embed-large` (1024 dimensions).
- **Process**: The script sends text chunks to your local Ollama instance to generate vector embeddings.
- **Configuration**: Your `.env` file determines which model and dimension size are used.
  ```env
  EMBEDDING_MODEL=nomic-embed-text
  EMBEDDING_DIMENSIONS=768
  ```

### LanceDB Storage

- **Module**: `agent/db_utils.py`
- **Why LanceDB?**: It's a zero-configuration, local-first vector database. No need to set up a separate database server like PostgreSQL.
- **Process**: The ingestion script saves the generated embeddings along with rich metadata (JLPT level, content type, source document) into a LanceDB table.
- **Location**: The database is stored locally in the `yukio_data/lancedb` directory.

### Metadata Extraction

During ingestion, the pipeline automatically extracts valuable metadata for each chunk:
- `has_japanese`: `true` or `false`
- `language`: `japanese` or `english`
- `content_type`: `vocabulary`, `grammar`, `kanji`, `dialogue`, or `lesson`
- `jlpt_level`: `N1`, `N2`, `N3`, `N4`, or `N5` (if found)
- `character_counts`: A breakdown of Hiragana, Katakana, and Kanji characters.

This metadata allows the AI agent to perform targeted searches, such as "find N3 grammar examples" or "get me a vocabulary list about food."

---

## 4. Troubleshooting

- **"Ollama connection failed"**:
  - Make sure Ollama is running. In a separate terminal, run `ollama serve`.
  - Test the connection with `curl http://localhost:11434/api/tags`.

- **"No markdown files found"**:
  - Ensure you have run `python scripts/convert_pdfs.py`.
  - Check that the output files exist in `data/japanese/markdown/`.

- **"spaCy model not found"**:
  - The Japanese model might not be installed. Run: `python -m spacy download ja_core_news_lg`.
  - The system will fall back to regex, but spaCy is recommended for quality.

- **"Embedding dimension mismatch"**:
  - Make sure the `EMBEDDING_DIMENSIONS` in your `.env` file matches the model you are using (e.g., 768 for `nomic-embed-text`).
