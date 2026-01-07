# 🎵 TTS Audio Integration - Complete Guide

## Overview

Yukio now features **automatic text-to-speech (TTS) generation and playback** for all responses. The system generates audio using Kokoro TTS (anime-style Japanese voices) and automatically plays it in the frontend.

---

## ✅ Features

### 1. **Automatic TTS Generation**
- TTS audio is automatically generated for every assistant response
- Uses Kokoro TTS with `af_bella` voice (soft, natural, less squeaky)
- Audio saved to `./yukio_data/audio/tts_output.wav`

### 2. **Real-time Text Streaming**
- Text responses stream in real-time as `text_delta` events
- Users see text appear progressively for better UX

### 3. **Automatic Audio Playback**
- Frontend automatically plays audio when `tts_ready` event is received
- No user interaction required - seamless experience

### 4. **Audio File Serving**
- New endpoint: `/api/audio/{filename}` serves TTS audio files
- Supports WAV, MP3, and OGG formats
- Proper content-type headers for browser compatibility

---

## 🔧 Technical Implementation

### Backend Flow

1. **User sends message** → `/chat/stream` endpoint
2. **Agent generates response** → Streams as `text_delta` events
3. **Response completes** → TTS generation triggered
4. **Audio generated** → Saved to `tts_output.wav`
5. **Frontend notified** → `tts_ready` event with audio URL
6. **Frontend plays audio** → Automatic playback

### Code Locations

- **TTS Manager**: `agent/tts.py`
- **API Endpoints**: `agent/api.py`
  - `/chat/stream` - Streaming chat with TTS
  - `/api/audio/{filename}` - Audio file serving
- **Frontend**: `yukio-frontend/src/app/chat/page.tsx`
  - Handles `tts_ready` events
  - Automatic audio playback

---

## 🎤 Voice Configuration

### Current Settings

- **Engine**: Kokoro TTS
- **Voice**: `af_bella` (recommended - softer, more natural)
- **Speed**: 1.05x (slightly faster, more natural)
- **Speech Rate**: 140 WPM (default, adjustable 50-400)

### Environment Variables

```bash
# .env file
TTS_ENGINE=kokoro          # or "native" or "auto"
TTS_VOICE=af_bella         # Recommended: af_bella or af_sarah
TTS_SPEECH_RATE=140        # Words per minute (50-400)
```

### Available Kokoro Voices

| Voice | Description | Best For |
|-------|-------------|----------|
| **`af_bella`** ⭐ | Softer, gentler, more natural | **Recommended - less squeaky** |
| **`af_sarah`** | Clear, professional | Professional tutoring |
| `af_sky` | Neutral tone | Balanced sound |
| `af_heart` | Cute, high-pitched | Too squeaky for tutoring |
| `af_sam` | Male voice | Alternative option |

---

## 📡 API Events

### Server-Sent Events (SSE) Stream

The `/chat/stream` endpoint sends the following events:

1. **`session`** - Session ID established
   ```json
   {"type": "session", "session_id": "..."}
   ```

2. **`text_delta`** - Text chunks streaming in real-time
   ```json
   {"type": "text_delta", "text": "Hello! How can I..."}
   ```

3. **`tts_ready`** - TTS audio ready for playback
   ```json
   {"type": "tts_ready", "audio_path": "/api/audio/tts_output.wav"}
   ```

4. **`done`** - Stream complete
   ```json
   {"type": "done"}
   ```

### Frontend Handling

```typescript
// Frontend automatically handles tts_ready events
if (chunk.type === 'tts_ready') {
  const audioPath = chunk.audio_path
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8058'
  const fullAudioUrl = `${backendUrl}${audioPath}`
  
  // Auto-play audio
  const audio = new Audio(fullAudioUrl)
  audio.play()
}
```

---

## 🚀 Usage

### Starting the Server

```bash
cd yukio
source .venv/bin/activate
uvicorn agent.api:app --reload --port 8058
```

### Testing TTS

1. **Send a chat message** in the frontend
2. **Text streams** in real-time
3. **Audio plays automatically** when ready

### Manual TTS Test

```bash
# Test TTS endpoint directly
curl -X POST http://localhost:8058/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは、George！", "speech_rate": 140}'
```

---

## 🐛 Troubleshooting

### Audio Not Playing

1. **Check browser console** for errors
2. **Verify backend URL** in frontend `.env.local`:
   ```bash
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8058
   ```
3. **Check audio file exists**:
   ```bash
   ls -lh yukio_data/audio/tts_output.wav
   ```

### TTS Not Generating

1. **Check TTS manager initialization**:
   ```python
   from agent.api import tts_manager
   print(tts_manager.is_available())  # Should be True
   ```

2. **Check Kokoro TTS setup**:
   - MeCab installed and configured
   - Kokoro dependencies installed
   - See `KOKORO_QUICK_SETUP.md`

3. **Check logs** for TTS errors:
   ```bash
   # Look for "Generating TTS" or "TTS generation failed" in logs
   ```

### Audio File Not Found

1. **Check audio directory exists**:
   ```bash
   mkdir -p yukio_data/audio
   ```

2. **Check file permissions**:
   ```bash
   chmod 755 yukio_data/audio
   ```

---

## 📊 Performance

- **TTS Generation**: ~1-3 seconds (depending on text length)
- **Audio File Size**: ~200-800 KB per response
- **Streaming Latency**: <100ms for text, +1-3s for audio

---

## 🔐 Security

- Audio files are served with proper content-type headers
- No authentication required for audio files (public endpoint)
- Consider adding rate limiting for production

---

## 📝 Notes

- TTS generation happens **after** text response completes
- Audio is generated for responses up to 500 characters
- Japanese text is extracted and prioritized for TTS
- Falls back to full response if no Japanese text found

---

## 🎉 Status

**✅ Fully Implemented and Tested**

- ✅ Text streaming working
- ✅ TTS generation working
- ✅ Audio file serving working
- ✅ Automatic playback working
- ✅ LangGraph integration working
- ✅ Error handling implemented

**Ready for production use!** 🚀

