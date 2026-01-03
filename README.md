# Yukio - Local AI Japanese Tutor

🏯 **Yukio** is a local-first, privacy-focused AI Japanese language tutor that runs entirely on your machine. No cloud APIs, no subscriptions—just you, your computer, and a comprehensive Japanese learning experience.

Powered by a modern, local-first AI stack:
- **Ollama**: For local LLM (Qwen2.5:14b) and embeddings.
- **LanceDB**: For zero-config, local vector storage.
- **uv**: For fast, modern Python package management.
- **Pydantic & FastAPI**: For a robust agent and API backend.
- **Dia**: For optional, high-quality Text-to-Speech voice generation.

## Quick Start

### 1. Prerequisites
- **Python 3.10-3.12**: Managed with `pyenv` is recommended.
- **Ollama**: Install from [ollama.ai](https://ollama.ai).
  ```bash
  # Pull the required models
  ollama pull qwen2.5:14b-instruct
  ollama pull nomic-embed-text
  ```
- **uv**: Install from [astral.sh](https://astral.sh/uv).
  ```bash
  # Install uv
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. Setup & Installation
From the project root, run the following to create the environment and install all dependencies:
```bash
# Create the virtual environment (uses .venv)
uv venv

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
Interact with Yukio through the command-line interface.
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the CLI
python cli.py

# Or run with voice enabled (see TTS docs for setup)
python cli.py --voice
```

## 📚 Documentation

This project's documentation has been consolidated into the `/docs` directory for clarity.

- **[Development Setup](./docs/development_setup.md)**: A complete guide to setting up your local environment with `uv` and `pyenv`.
- **[Ingestion Pipeline](./docs/ingestion.md)**: A detailed walkthrough of the data processing and ingestion workflow, from PDF to vector search.
- **[TTS / Voice Generation](./docs/tts_voice.md)**: Instructions for setting up and using the optional Text-to-Speech features.

## 🗺️ Project Roadmap

- [x] **Phase 1**: Data Preparation & Cleaning
- [x] **Phase 2**: Vector Database & Ingestion Pipeline
- [ ] **Phase 3**: Core Agent Development (In Progress)
- [ ] **Phase 4**: Memory & Progress Tracking
- [ ] **Phase 5**: API & Frontend

---
Built with 🏯 using a local-first, privacy-focused stack.
