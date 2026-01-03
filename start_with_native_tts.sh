#!/bin/bash
# Start Yukio API with native TTS enabled (much faster on Apple Silicon)

export YUKIO_USE_NATIVE_TTS=1

echo "🍎 Starting Yukio API with native TTS enabled..."
echo "   This will use macOS 'say' command instead of Dia TTS"
echo "   Much faster on M1/M2/M3 Macs!"
echo ""

cd "$(dirname "$0")"
source .venv/bin/activate
uvicorn agent.api:app --reload --port 8058

