# 🎌 Quick Setup: Enable Kokoro TTS

## ⚡ One-Command Setup

Run this in your terminal:

```bash
cd yukio
./scripts/setup_mecab.sh
```

Enter your password when prompted. That's it!

---

## 🔧 Manual Setup (Alternative)

If the script doesn't work, run these commands manually:

```bash
sudo mkdir -p /usr/local/etc
sudo ln -sf /opt/homebrew/etc/mecabrc /usr/local/etc/mecabrc
```

---

## ✅ Verify It Works

After setup, test Kokoro:

```bash
cd yukio
source .venv/bin/activate
python -c "from agent.tts import TTSManager; tts = TTSManager(engine='kokoro', voice='af_bella'); print('✅ Kokoro working!' if tts.engine == 'kokoro' else '❌ Still using fallback')"
```

Or test full TTS generation:

```bash
python -c "from agent.tts import TTSManager; tts = TTSManager(engine='kokoro', voice='af_bella'); audio = tts.generate_speech('こんにちは'); print('✅ Generated audio!' if audio is not None else '❌ Failed')"
```

---

## 🎤 What You'll Get

- **Voice**: `af_bella` (softer, less squeaky)
- **Speech Rate**: 140 WPM (slower, clearer)
- **Quality**: Anime-style Japanese TTS
- **Auto-enabled**: Once MeCab is configured, Kokoro will be used automatically

---

## ❓ Why This Is Needed

Kokoro uses MeCab for Japanese text processing. MeCab looks for its config file at `/usr/local/etc/mecabrc`, but Homebrew installs it at `/opt/homebrew/etc/mecabrc` on Apple Silicon Macs. The symlink makes MeCab find the config file.

---

**After setup, restart your API server and Kokoro will be used automatically!** 🎉

---

## 🔧 Technical Details

The code automatically handles MeCab dictionary format incompatibilities by:

1. **Detecting failures**: When the standard `fugashi.Tagger` fails with "Unknown dictionary format"
2. **Automatic fallback**: Falls back to `fugashi.GenericTagger` 
3. **Compatibility adapters**: Converts GenericTagger's tuple-based features to the object format expected by `cutlet`/`misaki`
4. **Full delegation**: All Node attributes are preserved for complete compatibility

**You don't need to worry about MeCab dictionary formats** - the code handles it automatically! The compatibility layer ensures Kokoro works even when MeCab's dictionary format is incompatible with the standard Tagger.

