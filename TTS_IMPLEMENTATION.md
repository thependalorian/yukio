# 🎵 TTS Implementation Summary

Complete implementation of automatic text-to-speech generation and playback for Yukio's responses.

---

## ✅ Implementation Status

**Status**: ✅ **Fully Implemented and Tested**

The system now automatically:
1. ✅ Generates TTS audio from text responses
2. ✅ Saves audio to `tts_output.wav`
3. ✅ Plays audio automatically using pygame

---

## 🎯 How It Works

### Flow

```
User Message
    ↓
Yukio generates text response
    ↓
TTS Manager converts text to speech
    ↓
Audio saved to: yukio_data/audio/tts_output.wav
    ↓
Audio played automatically (pygame)
```

### Integration Points

1. **Chat Stream Endpoint** (`/chat/stream`)
   - Automatically generates TTS after response completes
   - Saves to `tts_output.wav`
   - Sends `tts_ready` event to frontend

2. **TTS Manager** (`agent/tts.py`)
   - `generate_and_play()` - Generate, save, and play in one call
   - Supports both macOS native and Kokoro TTS
   - Automatic fallback between engines

---

## 🎤 Voice Configuration

### Current Settings (Less Squeaky)

- **Speech Rate**: 140 WPM (default, adjustable 50-400)
- **Voice**: 
  - macOS native: Kyoko (Japanese voice)
  - Kokoro: `af_bella` (softer, more natural) ⭐ Recommended

### Voice Options

#### For Kokoro TTS (when MeCab is fixed):

| Voice | Description | Best For |
|-------|-------------|----------|
| **`af_bella`** ⭐ | Softer, gentler, more natural | **Recommended - less squeaky** |
| **`af_sarah`** | Clear, professional | Professional tutoring |
| `af_sky` | Neutral tone | Balanced sound |
| `af_heart` | Cute, high-pitched | Too squeaky for tutoring |
| `af_sam` | Male voice | Alternative option |

### Configuration

**Environment Variables** (`.env`):
```bash
# TTS Engine
TTS_ENGINE=kokoro          # or "native" or "auto"

# Voice (for Kokoro)
TTS_VOICE=af_bella         # Recommended: af_bella or af_sarah

# Speech Rate (words per minute)
TTS_SPEECH_RATE=140        # Recommended: 120-150 for natural pace
```

**Code**:
```python
from agent.tts import TTSManager

# Natural, less squeaky voice
tts = TTSManager(
    engine="kokoro",
    voice="af_bella",      # Softer, more natural
    speech_rate=140        # Slower, clearer
)
```

---

## 📁 Output File

**Location**: `yukio_data/audio/tts_output.wav`

- Automatically generated after each response
- Overwritten with each new response
- Format: WAV, 44.1kHz (native) or 24kHz (Kokoro)
- Played automatically using pygame

---

## 🧪 Testing

### Test Script
```bash
cd yukio
python scripts/test_tts_playback.py
```

### Manual Test
```python
from agent.tts import generate_and_play

# Generate and play
generate_and_play(
    text="こんにちは！I am Yukio.",
    output_path="./yukio_data/audio/tts_output.wav",
    auto_play=True,
    speech_rate=140  # Slower, clearer
)
```

---

## 🎛️ Adjusting Speech Rate

### Recommended Rates

| Rate (WPM) | Description | Use Case |
|------------|------------|----------|
| 100-120 | Very slow, very clear | Beginners, complex explanations |
| 120-140 | Slow, clear ⭐ | **Recommended for tutoring** |
| 140-160 | Normal pace | General conversation |
| 160-200 | Fast | Quick responses |
| 200+ | Very fast | Not recommended |

### Change Rate

**Via API**:
```json
POST /api/tts
{
  "text": "Your text here",
  "speech_rate": 120  // Slower
}
```

**Via Environment**:
```bash
export TTS_SPEECH_RATE=120
```

**Via Code**:
```python
tts.generate_speech(text, speech_rate=120)
```

---

## 🔧 Troubleshooting

### Voice Too Squeaky

1. **Change voice** to `af_bella` or `af_sarah`:
   ```bash
   export TTS_VOICE=af_bella
   ```

2. **Slow down speech rate**:
   ```bash
   export TTS_SPEECH_RATE=120
   ```

3. **Use macOS native** (if Kokoro unavailable):
   ```bash
   export TTS_ENGINE=native
   ```

### Audio Not Playing

1. **Check pygame installation**:
   ```bash
   python -c "import pygame; print('✅ pygame installed')"
   ```

2. **Check audio file exists**:
   ```bash
   ls -lh yukio_data/audio/tts_output.wav
   ```

3. **Test playback manually**:
   ```bash
   afplay yukio_data/audio/tts_output.wav  # macOS
   ```

### Kokoro Not Working

See `KOKORO_SETUP.md` for MeCab configuration fix.

---

## 📊 Current Implementation

### Files Modified

1. **`agent/tts.py`**
   - Added `generate_and_play()` method
   - Added `_play_audio()` method with pygame support
   - Updated default voice to `af_bella`
   - Updated default speech rate to 140 WPM

2. **`agent/api.py`**
   - Integrated TTS generation into `/chat/stream` endpoint
   - Automatically generates TTS after response
   - Saves to `tts_output.wav`
   - Sends `tts_ready` event to frontend

3. **`agent/models.py`**
   - Updated `TTSRequest` default speech rate to 140

### New Files

- `scripts/test_tts_playback.py` - Test script
- `scripts/test_kokoro_voices.py` - Voice comparison script
- `AUDIO_LIBRARIES_DOCS.md` - Complete documentation
- `TTS_IMPLEMENTATION.md` - This file

---

## 🎯 Next Steps

1. **Fix MeCab** for Kokoro TTS:
   ```bash
   sudo ln -sf /opt/homebrew/etc/mecabrc /usr/local/etc/mecabrc
   ```

2. **Test different voices**:
   ```bash
   python scripts/test_kokoro_voices.py
   ```

3. **Adjust speech rate** if needed (120-140 WPM recommended)

4. **Frontend integration** (optional):
   - Listen for `tts_ready` event
   - Play audio from frontend if desired

---

## ✅ Summary

- ✅ TTS generation: **Working**
- ✅ Audio saving: **Working** (`tts_output.wav`)
- ✅ Automatic playback: **Working** (pygame)
- ✅ Slower speech rate: **140 WPM** (configurable)
- ✅ Better voice options: **af_bella** (less squeaky)
- ✅ Complete flow: **Text → TTS → Save → Play**

**The system is ready to use!** 🎉

---

**Last Updated**: 2025-01-07

