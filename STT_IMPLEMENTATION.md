# STT (Speech-to-Text) Implementation Guide

## Overview

Yukio now includes **Speech-to-Text (STT)** functionality for pronunciation practice, closing the critical gap identified in the competitive analysis. This implementation uses **Whisper** (local-first) to maintain Yukio's privacy-focused architecture.

## Features

✅ **Local Whisper-based STT** - Privacy-focused, no cloud dependencies  
✅ **Japanese Speech Recognition** - Optimized for Japanese language  
✅ **Pronunciation Scoring** - 0-100 score with detailed feedback  
✅ **Sound-by-Sound Analysis** - Compares transcription with target text  
✅ **Romaji Conversion** - Automatic conversion for comparison  

## Installation

### 1. Install Whisper

```bash
# Activate virtual environment
source .venv/bin/activate

# Install Whisper (large download, ~500MB-3GB depending on model)
pip install openai-whisper

# Or using uv
uv pip install openai-whisper
```

### 2. Install Additional Dependencies

```bash
# pykakasi is already in pyproject.toml for romaji conversion
# Ensure it's installed
uv pip install pykakasi
```

### 3. Download Whisper Model

Whisper will automatically download the model on first use. Model sizes:

- **tiny** (~75MB) - Fastest, least accurate
- **base** (~150MB) - **Recommended** - Good balance
- **small** (~500MB) - Better accuracy
- **medium** (~1.5GB) - High accuracy
- **large** (~3GB) - Best accuracy, slowest

Default: `base` (configured via `WHISPER_MODEL_SIZE` environment variable)

## Configuration

### Environment Variables

Add to `.env`:

```env
# Whisper model size (tiny, base, small, medium, large)
WHISPER_MODEL_SIZE=base
```

### Model Selection Guide

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 75MB | Very Fast | Basic | Quick testing |
| **base** | 150MB | Fast | Good | **Recommended** |
| small | 500MB | Medium | Better | Higher accuracy needed |
| medium | 1.5GB | Slow | High | Production quality |
| large | 3GB | Very Slow | Best | Maximum accuracy |

## API Endpoint

### `POST /voice/analyze`

Analyze pronunciation of recorded audio.

**Request:**
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `audio` (file): Audio file (WAV, MP3, M4A, WebM, OGG)
  - `target_text` (string): Target Japanese text
  - `target_romaji` (string, optional): Target romaji

**Response:**
```json
{
  "transcript": "こんにちは",
  "score": 95,
  "feedback": "Excellent pronunciation! Very close to native.",
  "target_text": "こんにちは",
  "target_romaji": "konnichiwa",
  "transcribed_romaji": "konnichiwa"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8058/voice/analyze \
  -F "audio=@recording.wav" \
  -F "target_text=こんにちは" \
  -F "target_romaji=konnichiwa"
```

## Frontend Integration

The frontend voice practice page (`/practice/voice`) now:

1. ✅ Records audio using browser MediaRecorder API
2. ✅ Sends audio to `/voice/analyze` endpoint
3. ✅ Displays pronunciation score (0-100)
4. ✅ Shows detailed feedback
5. ✅ Provides improvement tips

### Usage in Frontend

```typescript
import { api } from '@/lib/api'

// Analyze pronunciation
const result = await api.analyzePronunciation(
  audioBlob,           // Blob from MediaRecorder
  "こんにちは",        // Target Japanese text
  "konnichiwa"         // Optional: target romaji
)

console.log(result.score)      // 0-100
console.log(result.feedback)   // Feedback message
console.log(result.transcript) // What was transcribed
```

## Pronunciation Scoring Algorithm

The scoring algorithm uses:

1. **Word-level matching** (60% weight)
   - Compares transcribed words with target romaji
   - Checks for missing or incorrect words

2. **Character-level matching** (40% weight)
   - Compares Japanese characters
   - Useful for detecting partial matches

3. **Feedback Generation**
   - Score >= 90: "Excellent pronunciation! Very close to native."
   - Score >= 80: "Good pronunciation! Minor improvements needed."
   - Score >= 70: "Decent pronunciation. Practice the sounds more carefully."
   - Score >= 60: "Pronunciation needs work. Listen to the native audio and try again."
   - Score < 60: "Pronunciation needs significant improvement. Focus on each syllable."

## Architecture

```
┌─────────────────┐
│  Frontend       │
│  Voice Practice │
│  (MediaRecorder)│
└────────┬────────┘
         │ POST /voice/analyze
         │ (multipart/form-data)
         │
┌────────▼────────┐
│  Backend API    │
│  /voice/analyze │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│Whisper│ │pykakasi│
│  STT  │ │ Romaji │
└───────┘ └────────┘
```

## Performance Considerations

### Model Size vs. Speed

- **tiny**: ~0.5s per transcription
- **base**: ~1-2s per transcription
- **small**: ~3-5s per transcription
- **medium**: ~5-10s per transcription
- **large**: ~10-20s per transcription

**Recommendation**: Use `base` for good balance of speed and accuracy.

### Apple Silicon Optimization

Whisper uses PyTorch, which has good Apple Silicon support. However:

- First transcription may be slower (model loading)
- Subsequent transcriptions are faster (model cached)
- Consider using `tiny` or `base` on older Macs

## Troubleshooting

### "STT not available" Error

**Solution**: Install Whisper
```bash
pip install openai-whisper
```

### "Failed to load Whisper model" Error

**Solution**: 
- Check internet connection (first-time model download)
- Ensure sufficient disk space (150MB-3GB depending on model)
- Try smaller model size (`WHISPER_MODEL_SIZE=tiny`)

### Slow Transcription

**Solutions**:
- Use smaller model (`WHISPER_MODEL_SIZE=tiny` or `base`)
- Reduce audio length (limit to 5-10 seconds)
- Ensure PyTorch is using GPU (if available)

### Poor Accuracy

**Solutions**:
- Use larger model (`WHISPER_MODEL_SIZE=small` or `medium`)
- Ensure clear audio recording
- Reduce background noise
- Speak clearly and at normal pace

### "pykakasi not available" Warning

**Solution**: Install pykakasi
```bash
pip install pykakasi
```

Note: Romaji conversion will fall back to text-as-is if pykakasi unavailable.

## Testing

### Test STT Module Directly

```python
from agent.stt import STTManager

# Initialize
stt = STTManager(model_size="base")

# Test transcription
transcript = stt.transcribe("path/to/audio.wav")
print(f"Transcribed: {transcript}")

# Test pronunciation analysis
result = stt.analyze_pronunciation(
    audio_path="path/to/audio.wav",
    target_text="こんにちは",
    target_romaji="konnichiwa"
)
print(f"Score: {result['score']}%")
print(f"Feedback: {result['feedback']}")
```

### Test API Endpoint

```bash
# Record audio first, then:
curl -X POST http://localhost:8058/voice/analyze \
  -F "audio=@test_recording.wav" \
  -F "target_text=こんにちは" \
  -F "target_romaji=konnichiwa"
```

## Comparison with Competitors

| Feature | Yukio | Falou | Duolingo |
|---------|-------|-------|----------|
| **STT Engine** | Whisper (local) | Cloud STT | Cloud STT |
| **Privacy** | ✅ Fully local | ❌ Cloud | ❌ Cloud |
| **Pronunciation Scoring** | ✅ 0-100 score | ✅ Detailed feedback | ✅ Basic feedback |
| **Sound Analysis** | ✅ Word + char level | ✅ Sound-by-sound | ⚠️ Basic |
| **Offline** | ✅ Yes | ❌ No | ❌ No |

**Yukio's Advantage**: Fully local, privacy-focused STT with competitive features.

## Future Enhancements

### Potential Improvements

1. **Advanced Pronunciation Analysis**
   - Phonetic comparison (using IPA)
   - Pitch accent detection
   - Syllable-by-syllable breakdown

2. **Real-time Feedback**
   - Live transcription during recording
   - Real-time score updates

3. **Multiple Attempts**
   - Track improvement over time
   - Show progress graph

4. **Native Speaker Comparison**
   - Compare with reference audio
   - Visual waveform comparison

5. **Custom Scoring Models**
   - Train model on user's accent
   - Personalized feedback

## References

- [Whisper Documentation](https://github.com/openai/whisper)
- [pykakasi Documentation](https://github.com/miurahr/pykakasi)
- [Competitive Analysis](./COMPETITIVE_ANALYSIS.md)

---

**Status**: ✅ Implemented  
**Version**: 1.0  
**Last Updated**: January 2025

