# 🎌 Kokoro TTS Setup for Anime-Style Voice

Yukio now supports **Kokoro TTS** for anime-style Japanese voices! This gives Yukio a cute, high-pitched "waifu" voice perfect for a Japanese tutor.

## Installation

### Option 1: Install Kokoro TTS (Recommended for Anime Voice)

**Step 1: Install Python dependencies**
```bash
cd yukio
uv add kokoro pyopenjtalk fugashi mojimoji soundfile
```

**Step 2: Install MeCab (system dependency for Japanese text processing)**
```bash
# On macOS with Homebrew:
brew install mecab mecab-ipadic

# Fix MeCab config path (required for Apple Silicon Macs):
sudo mkdir -p /usr/local/etc
sudo ln -sf /opt/homebrew/etc/mecabrc /usr/local/etc/mecabrc
```

**Step 3: Verify installation**
```bash
python -c "from kokoro import KPipeline; p = KPipeline(lang_code='j'); print('✅ Kokoro ready!')"
```

### Option 2: Use macOS Native TTS (Default)

If you don't install Kokoro, Yukio will automatically use macOS native TTS (Kyoko voice).

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# TTS Engine: "native" (macOS say), "kokoro" (anime-style), or "auto" (auto-select)
TTS_ENGINE=kokoro

# Kokoro voice (optional, default: "af_bella" - softer, more natural)
# Available voices: af_bella (recommended), af_sarah, af_sky, af_heart, etc.
# See: https://huggingface.co/NeuML/kokoro-int8-onnx#speaker-reference
TTS_VOICE=af_bella

# Speech rate in words per minute (50-400, default: 140)
# Lower = slower, clearer speech (recommended: 120-150 for natural pace)
TTS_SPEECH_RATE=140
```

### Available Kokoro Voices

Kokoro supports multiple voices. For a natural, less squeaky voice:

- **`af_bella`** ⭐ **Recommended** - Softer, gentler, more natural voice (less squeaky)
- **`af_sarah`** - Clear, professional voice
- **`af_sky`** - Neutral tone
- **`af_heart`** - Cute, high-pitched (may be too squeaky)
- **`af_sam`** - Male voice
- See [Kokoro model card](https://huggingface.co/NeuML/kokoro-int8-onnx#speaker-reference) for full list

**Note**: For Japanese tutoring, `af_bella` or `af_sarah` are recommended for a more natural, professional sound.

## Usage

### Automatic Selection

If `TTS_ENGINE=auto` (default), Yukio will:
1. Try Kokoro first (if installed) - anime-style voice
2. Fall back to macOS native TTS if Kokoro unavailable

### Manual Selection

```python
from agent.tts import TTSManager

# Use Kokoro with natural voice (less squeaky)
tts = TTSManager(engine="kokoro", voice="af_bella", speech_rate=140)

# Use macOS native
tts = TTSManager(engine="native")

# Check availability
if tts.is_available():
    audio = tts.generate_speech("こんにちは、George！")
    tts.save_audio("output.wav", audio)
```

## API Usage

The `/api/tts` endpoint automatically uses the configured engine:

```bash
curl -X POST http://localhost:8058/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"こんにちは！I am Yukio, your Japanese tutor.","speech_rate":140}' \
  --output yukio_voice.wav
```

## Comparison

| Feature | macOS Native | Kokoro TTS |
|---------|--------------|------------|
| **Voice Style** | Professional Japanese | Anime-style, cute |
| **Speed** | Fast (native) | Fast (on-device) |
| **Quality** | Good | Excellent |
| **Installation** | Built-in | `pip install kokoro` |
| **File Size** | 0 MB | ~100 MB model |
| **Best For** | Quick testing | Production anime voice |

## Troubleshooting

### Kokoro Not Found

If you see "Kokoro TTS not available":
```bash
pip install kokoro
```

### Voice Not Working

Check that Kokoro is installed:
```bash
python -c "from kokoro import KPipeline; print('✅ Kokoro available')"
```

### Fallback to Native

If Kokoro fails, Yukio automatically falls back to macOS native TTS.

## Example: Testing Both Voices

```python
from agent.tts import TTSManager

# Test Kokoro (anime voice)
kokoro_tts = TTSManager(engine="kokoro", voice="af_heart")
if kokoro_tts.is_available():
    audio = kokoro_tts.generate_speech("こんにちは！")
    kokoro_tts.save_audio("kokoro_voice.wav", audio)

# Test Native (professional voice)
native_tts = TTSManager(engine="native")
if native_tts.is_available():
    audio = native_tts.generate_speech("こんにちは！")
    native_tts.save_audio("native_voice.wav", audio)
```

## Notes

- Kokoro TTS supports **Japanese text directly** (no romaji conversion needed)
- The model is downloaded automatically on first use (~100 MB)
- Works on both Apple Silicon and Intel Macs
- For natural, less squeaky voice, use `af_bella` or `af_sarah` with `speech_rate=120-140`
- Avoid `af_heart` if it sounds too squeaky - try `af_bella` instead

Enjoy your anime-style Yukio voice! 🎌✨

