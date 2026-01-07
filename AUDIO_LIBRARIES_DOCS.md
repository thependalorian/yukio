# 🎵 Audio Libraries Documentation

Complete documentation for pygame, playsound, and Kokoro TTS used in Yukio.

---

## 📚 Table of Contents

1. [Pygame](#pygame)
2. [Playsound](#playsound)
3. [Kokoro TTS](#kokoro-tts)

---

## 🎮 Pygame

### Official Resources

- **Website**: https://www.pygame.org/
- **Documentation**: https://www.pygame.org/docs/
- **GitHub**: https://github.com/pygame/pygame
- **PyPI**: https://pypi.org/project/pygame/

### Installation

```bash
pip install pygame
# or with uv
uv add pygame
```

### Basic Usage for Audio Playback

```python
import pygame
import time

# Initialize pygame mixer
pygame.mixer.init()

# Load and play audio file
pygame.mixer.music.load('audio.wav')
pygame.mixer.music.play()

# Wait for playback to finish
while pygame.mixer.music.get_busy():
    pygame.time.Clock().tick(10)

# Clean up
pygame.mixer.quit()
```

### Advanced Usage

```python
import pygame

# Initialize with specific settings
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Load sound (for short sounds)
sound = pygame.mixer.Sound('beep.wav')
sound.play()

# Load music (for longer audio)
pygame.mixer.music.load('speech.wav')
pygame.mixer.music.set_volume(0.7)  # 0.0 to 1.0
pygame.mixer.music.play()

# Control playback
pygame.mixer.music.pause()
pygame.mixer.music.unpause()
pygame.mixer.music.stop()

# Check if playing
if pygame.mixer.music.get_busy():
    print("Audio is playing")
```

### Key Features

- Cross-platform (Windows, macOS, Linux)
- Supports WAV, OGG, MP3 formats
- Low latency audio playback
- Volume control
- Playback status checking

---

## 🔊 Playsound

### Official Resources

- **GitHub**: https://github.com/TaylorSMarks/playsound
- **PyPI**: https://pypi.org/project/playsound/

### Installation

```bash
pip install playsound
# or with uv
uv add playsound
```

### Basic Usage

```python
from playsound import playsound

# Simple playback (blocking)
playsound('audio.wav')

# With error handling
try:
    playsound('audio.wav')
except Exception as e:
    print(f"Error playing audio: {e}")
```

### Advanced Usage

```python
from playsound import playsound
import threading

# Non-blocking playback
def play_audio_async(file_path):
    def play():
        playsound(file_path)
    thread = threading.Thread(target=play)
    thread.daemon = True
    thread.start()
    return thread

# Play audio in background
thread = play_audio_async('speech.wav')
# Continue with other code while audio plays
```

### Key Features

- Pure Python (no dependencies)
- Simple API
- Cross-platform
- Supports WAV, MP3, OGG
- Blocking by default (can be made async)

### Limitations

- No volume control
- No pause/resume
- Blocking by default
- Some platforms may have issues with certain formats

---

## 🎌 Kokoro TTS

### Official Resources

- **Website**: https://www.kokorotts.io/
- **GitHub (hexgrad)**: https://github.com/hexgrad/kokoro
- **HuggingFace Model**: https://huggingface.co/NeuML/kokoro-int8-onnx
- **PyPI**: https://pypi.org/project/kokoro/

### Installation

```bash
pip install kokoro pyopenjtalk fugashi mojimoji
# or with uv
uv add kokoro pyopenjtalk fugashi mojimoji

# System dependency (macOS)
brew install mecab mecab-ipadic
```

### Basic Usage

```python
from kokoro import KPipeline

# Initialize pipeline for Japanese
pipeline = KPipeline(lang_code="j")  # "j" = Japanese, "a" = American English

# Generate speech
text = "こんにちは、George！"
audio_chunks = []

for _gs, _ps, audio in pipeline(text, voice="af_heart", speed=1.0):
    audio_chunks.append(audio)

# Concatenate chunks
import numpy as np
full_audio = np.concatenate(audio_chunks)

# Save to file
import soundfile as sf
sf.write("output.wav", full_audio, 24000)  # Kokoro uses 24kHz
```

### Available Voices

Kokoro supports multiple voices. For anime-style "waifu" voice:

- **`af_heart`** ⭐ - Cute, high-pitched anime voice (recommended)
- **`af_bella`** - Softer, gentle voice
- **`af_sarah`** - Clear, professional voice
- **`af_sky`** - Neutral voice
- **`af_sam`** - Male voice

See full list: https://huggingface.co/NeuML/kokoro-int8-onnx#speaker-reference

### Language Codes

- `"a"` - American English
- `"j"` - Japanese
- `"f"` - French
- `"k"` - Korean
- `"c"` - Chinese

### Advanced Usage

```python
from kokoro import KPipeline
import numpy as np
import soundfile as sf

# Initialize with custom settings
pipeline = KPipeline(lang_code="j")

# Generate with custom speed (0.5 = slow, 2.0 = fast)
text = "こんにちは！I am Yukio, your Japanese tutor."
audio_chunks = []

for _gs, _ps, audio in pipeline(
    text,
    voice="af_heart",      # Anime-style voice
    speed=0.8,              # Slower for clarity
    split_pattern=r"\n+"   # Split on newlines
):
    if isinstance(audio, np.ndarray):
        audio_chunks.append(audio.astype(np.float32))
    else:
        audio_chunks.append(np.array(audio, dtype=np.float32))

# Combine all chunks
if audio_chunks:
    full_audio = np.concatenate(audio_chunks)
    
    # Save as WAV (24kHz sample rate)
    sf.write("yukio_speech.wav", full_audio, 24000)
    print(f"Generated {len(full_audio)} samples")
```

### Integration with Yukio

```python
from agent.tts import TTSManager

# Use Kokoro for anime voice
tts = TTSManager(engine="kokoro", voice="af_heart", speech_rate=160)

if tts.is_available():
    audio = tts.generate_speech("こんにちは！")
    tts.save_audio("output.wav", audio)
```

### Troubleshooting

**MeCab Error (macOS)**:
```bash
# Fix MeCab config path for Apple Silicon
sudo mkdir -p /usr/local/etc
sudo ln -sf /opt/homebrew/etc/mecabrc /usr/local/etc/mecabrc
```

**Missing Dependencies**:
```bash
pip install pyopenjtalk fugashi mojimoji
brew install mecab mecab-ipadic
```

---

## 🎯 Comparison

| Feature | Pygame | Playsound | Kokoro TTS |
|---------|--------|-----------|------------|
| **Purpose** | Game development, audio playback | Simple audio playback | Text-to-speech generation |
| **Complexity** | Medium | Low | High |
| **Dependencies** | SDL libraries | None | Multiple (MeCab, etc.) |
| **Volume Control** | ✅ Yes | ❌ No | N/A |
| **Pause/Resume** | ✅ Yes | ❌ No | N/A |
| **Non-blocking** | ✅ Yes | ⚠️ With threading | ✅ Yes |
| **Best For** | Interactive apps, games | Quick audio playback | TTS generation |

---

## 💡 Usage Examples in Yukio

### Example 1: Play TTS Audio with Pygame

```python
from agent.tts import TTSManager
import pygame

tts = TTSManager(engine="kokoro", voice="af_heart")
audio = tts.generate_speech("こんにちは！")

# Save temporarily
tts.save_audio("temp.wav", audio)

# Play with pygame
pygame.mixer.init()
pygame.mixer.music.load("temp.wav")
pygame.mixer.music.play()

while pygame.mixer.music.get_busy():
    pygame.time.Clock().tick(10)
```

### Example 2: Play TTS Audio with Playsound

```python
from agent.tts import TTSManager
from playsound import playsound

tts = TTSManager(engine="kokoro", voice="af_heart")
audio = tts.generate_speech("こんにちは！")

# Save and play
tts.save_audio("temp.wav", audio)
playsound("temp.wav")
```

### Example 3: Direct Kokoro Usage

```python
from kokoro import KPipeline
import numpy as np
import soundfile as sf

pipeline = KPipeline(lang_code="j")
text = "こんにちは、George！"

audio_chunks = []
for _gs, _ps, audio in pipeline(text, voice="af_heart", speed=0.8):
    audio_chunks.append(audio)

full_audio = np.concatenate(audio_chunks)
sf.write("output.wav", full_audio, 24000)
```

---

## 📖 Additional Resources

### Pygame
- Tutorial: https://www.pygame.org/wiki/tutorials
- Examples: https://github.com/pygame/pygame/tree/main/examples

### Playsound
- GitHub Issues: https://github.com/TaylorSMarks/playsound/issues
- Alternative: Consider `pydub` + `simpleaudio` for more control

### Kokoro
- Model Card: https://huggingface.co/NeuML/kokoro-int8-onnx
- Voice Samples: Check HuggingFace model card for audio examples
- Community: GitHub discussions and issues

---

## ✅ Quick Reference

```python
# Pygame - Best for interactive apps
pygame.mixer.init()
pygame.mixer.music.load('file.wav')
pygame.mixer.music.play()

# Playsound - Simplest option
from playsound import playsound
playsound('file.wav')

# Kokoro - TTS generation
from kokoro import KPipeline
pipeline = KPipeline(lang_code="j")
for _gs, _ps, audio in pipeline("text", voice="af_heart"):
    # Process audio chunks
    pass
```

---

**Last Updated**: 2025-01-07

