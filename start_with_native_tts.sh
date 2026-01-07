#!/bin/bash
# Start Yukio API with native macOS TTS

echo "🍎 Starting Yukio API with native macOS TTS..."
echo "   Using macOS 'say' command for fast, reliable TTS"
echo ""

cd "$(dirname "$0")"
source .venv/bin/activate
uvicorn agent.api:app --reload --port 8058

