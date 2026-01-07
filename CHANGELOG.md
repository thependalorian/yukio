# Changelog

All notable changes to Yukio will be documented in this file.

## [Unreleased]

### Fixed
- **Vector Search Error**: Fixed critical `'chunk_id'` KeyError by updating field mappings to use LanceDB's `id` field and `_distance` for similarity scores
- **TTS Performance**: Added macOS native TTS fallback for Apple Silicon (M1/M2/M3) - 100x faster than Dia TTS
- **Mem0 Warnings**: Installed mem0ai package to enable memory features
- **Font Loading**: Fixed Google Fonts loading issues with graceful fallback
- **Chat UI**: Fixed duplicate loading indicators in chat bubbles
- **Response Formatting**: Added markdown rendering for better UX in chat responses
- **Raw Search Results**: Removed raw search results and metadata from agent responses

### Added
- **Native TTS Support**: macOS `say` command integration for fast TTS on Apple Silicon
- **Response Cleaning**: Automatic filtering of search result references and metadata
- **Diagnostic Scripts**: Added `scripts/fix_vector_search.py` for schema diagnosis
- **Helper Scripts**: Added `start_with_native_tts.sh` for easy native TTS setup
- **Documentation**: Added `FIXES_APPLIED.md` and `ISSUES_FIXED.md` with detailed fix documentation
- **Git Ignore**: Comprehensive `.gitignore` for Python projects

### Changed
- **System Prompt**: Updated to prevent raw search results in responses
- **CI Workflow**: Updated to handle optional mem0ai dependency gracefully
- **Error Handling**: Improved error handling in vector search tools with better field validation
- **Frontend**: Added markdown rendering with react-markdown for formatted responses

### Technical Details

#### Vector Search Fix
- Updated `agent/tools.py` to use correct LanceDB field names:
  - `id` instead of `chunk_id`
  - `_distance` converted to similarity score (1 - distance/2)
  - Added fallbacks for field name variations

#### TTS Improvements
- Added `_speak_native()` method in `agent/tts.py`
- Supports Japanese voices (Kyoko, Otoya) with fallback
- Generates audio at 44100 Hz to match API expectations
- Enable with `YUKIO_USE_NATIVE_TTS=1` environment variable

#### Response Cleaning
- Added `clean_agent_response()` function to filter:
  - Japanese search result phrases
  - English metadata references
  - Document source citations
  - Chunk IDs and scores

---

## [0.1.0] - Initial Release

### Features
- Local-first AI Japanese tutor
- RAG-powered learning content generation
- Progress tracking and gamification
- CLI and API interfaces
- Frontend web application

