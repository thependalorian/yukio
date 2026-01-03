# Yukio TTS: Voice Generation with Dia

This guide covers the setup, usage, and performance of the Text-to-Speech (TTS) system in Yukio, which is powered by the Dia 1.6B model from Nari Labs.

## 1. Overview of Dia TTS

Dia is a 1.6B parameter text-to-speech model that can directly generate highly realistic dialogue from a transcript.

- **Multi-Speaker Dialogue**: Generate conversations using `[S1]` and `[S2]` tags.
- **Non-Verbal Sounds**: Can produce laughter `(laughs)`, sighs `(sighs)`, and more.
- **Voice Cloning**: Condition the output on an audio prompt to clone a voice.
- **Open Source**: Licensed under Apache 2.0.

**Important Limitation**: Dia currently only supports **English text**. For Japanese, you must provide romanized text (Romaji). Native Japanese support is planned for future versions.

## 2. Installation and Setup

The TTS feature is **optional**. Yukio will function perfectly without it.

### Step 1: Install Dependencies

The `dia` sub-project is included in this repository. To install it and its dependencies (`torch`, `torchaudio`, `descript-audio-codec`, etc.), run the following command from the project root:

```bash
# This uses the uv installer we set up
uv pip install -e dia
```
This command installs `dia` in "editable" mode, which is the recommended approach.

### Step 2: Model Download (First Run)

The first time you use the TTS feature, the Dia 1.6B model weights (~3GB) will be downloaded automatically from Hugging Face and cached on your system (usually in `~/.cache/huggingface/hub/`).

### Step 3: Verify Installation

You can verify that the TTS manager can successfully load the model by running:

```bash
python -c "from agent.tts import TTSManager; tts = TTSManager(); print('TTS available:', tts.is_available())"
```
If the output is `TTS available: True`, you are ready to go!

## 3. Usage

### Command-Line Interface (CLI)

To enable voice generation in the CLI, use the `--voice` flag:
```bash
python cli.py --voice
```
When enabled, the CLI will:
- Automatically convert Yukio's Japanese responses to Romaji.
- Generate audio for the response.
- Save the audio file to `yukio_data/audio/`.
- Attempt to play the audio automatically.

### Python API (`TTSManager`)

For more advanced usage, you can use the `TTSManager` class located in `agent/tts.py`.

#### Basic Generation
```python
from agent.tts import TTSManager

# Initialize the manager
tts = TTSManager()

if tts.is_available():
    # Generate speech from English text
    audio = tts.generate_speech("[S1] Hello! Welcome to Yukio.")

    # Save the audio to a file
    tts.save_audio("output.wav", audio)
```

#### Japanese Text (Romaji)
The `format_japanese_text` method automatically handles the conversion from Japanese characters to Romaji.
```python
# The TTSManager handles Romaji conversion automatically
japanese_response = "こんにちは、ジョージさん！"
romaji_text = tts.format_japanese_text(japanese_response)
# romaji_text will be "[S1] konnichiha, jo-ji san!"

audio = tts.generate_speech(romaji_text)
tts.save_audio("japanese_audio.wav", audio)
```

#### Dialogue and Non-Verbal Sounds
```python
dialogue = (
    "[S1] That's hilarious! (laughs) "
    "[S2] Let me think... (sighs) "
    "[S1] Would you like to learn Japanese? "
    "[S2] Yes, that sounds wonderful!"
)

audio = tts.generate_speech(dialogue)
tts.save_audio("dialogue.wav", audio)
```

## 4. Performance and Hardware

### GPU (Recommended)
- **VRAM**: ~10GB required for optimal performance.
- **Recommended Cards**: NVIDIA RTX 30-series/40-series.
- **Performance**: With a GPU like an RTX 4090, generation is faster than real-time.

### CPU
- **Fallback**: Dia will automatically use the CPU if a compatible GPU is not found.
- **Performance**: Generation is **significantly slower** than real-time. A short phrase can take several minutes. It is not recommended for interactive use but is fine for testing or offline generation.

### Apple Silicon (Mac M1/M2/M3)
- **Current Status**: **Very Slow**.
- **Problem**: The MPS (Metal Performance Shaders) backend has limitations that cause very slow performance (e.g., 5+ minutes for a 30-second audio clip).
- **Workaround**: The `TTSManager` automatically detects MPS and falls back to the CPU, but it remains slow.
- **Recommendation**: For now, it is recommended to **not** use the `--voice` flag on Apple Silicon Macs unless you are prepared to wait.

## 5. Troubleshooting

- **"Dia TTS not available"**:
  - This means the installation in Step 1 failed.
  - Run `uv pip install -e dia` again and check for errors.

- **CUDA Out of Memory**:
  - Your GPU may not have enough VRAM (~10GB needed).
  - Close other GPU-intensive applications.
  - The system should fall back to CPU automatically.

- **Slow Generation on Mac**:
  - This is expected due to the performance issues with Apple Silicon noted above. There is currently no fix other than using a different machine with an NVIDIA GPU.

- **Model Download Fails**:
  - Check your internet connection.
  - You can try clearing the Hugging Face cache at `~/.cache/huggingface/hub/` and trying again.
