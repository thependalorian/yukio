# 🔧 MeCab Configuration Setup for Kokoro TTS

MeCab is required for Kokoro TTS to work with Japanese text. This guide helps you fix the configuration path issue.

---

## ❌ Problem

When using Kokoro TTS, you might see this error:

```
Failed initializing MeCab. Please see the README for possible solutions:
arguments: [b'fugashi', b'-C']
param.cpp(69) [ifs] no such file or directory: /usr/local/etc/mecabrc
```

**Why?** 
- MeCab (via fugashi) looks for config at `/usr/local/etc/mecabrc`
- Homebrew on Apple Silicon installs it to `/opt/homebrew/etc/mecabrc`
- The paths don't match!

---

## ✅ Solution Options

### Option 1: Automatic Setup Script (Recommended)

Run the setup script:

```bash
cd yukio
./scripts/setup_mecab.sh
```

This script will:
1. Find your MeCab config file
2. Create a symlink from `/usr/local/etc/mecabrc` → `/opt/homebrew/etc/mecabrc`
3. Verify the setup

**Note**: Requires `sudo` access to create the symlink.

### Option 2: Manual Symlink

If you prefer to do it manually:

```bash
# Create the directory if it doesn't exist
sudo mkdir -p /usr/local/etc

# Create symlink
sudo ln -sf /opt/homebrew/etc/mecabrc /usr/local/etc/mecabrc

# Verify
ls -la /usr/local/etc/mecabrc
```

### Option 3: Environment Variable (Already Implemented)

The code automatically sets `MECAB_DEFAULT_RC` and `MECABRC` environment variables, but fugashi might check the file path directly, so the symlink is more reliable.

---

## 🧪 Verification

After setup, test that Kokoro works:

```bash
cd yukio
python -c "from kokoro import KPipeline; p = KPipeline(lang_code='j'); print('✅ Kokoro ready!')"
```

If you see `✅ Kokoro ready!`, you're all set!

---

## 📋 What the Script Does

1. **Checks for MeCab config**:
   - `/opt/homebrew/etc/mecabrc` (Apple Silicon)
   - `/usr/local/etc/mecabrc` (Intel)

2. **Creates symlink**:
   - `/usr/local/etc/mecabrc` → `/opt/homebrew/etc/mecabrc`

3. **Verifies setup**:
   - Checks symlink exists and points correctly

---

## 🔍 Troubleshooting

### "Permission denied"

The script needs `sudo` to create the symlink. Enter your password when prompted.

### "MeCab config not found"

Install MeCab first:
```bash
brew install mecab mecab-ipadic
```

### "Symlink already exists"

If a symlink already exists pointing to the wrong file, the script will ask if you want to replace it.

### Still not working?

Check the symlink:
```bash
ls -la /usr/local/etc/mecabrc
```

Should show:
```
lrwxr-xr-x ... /usr/local/etc/mecabrc -> /opt/homebrew/etc/mecabrc
```

---

## 📝 MeCab Config File Location

**Apple Silicon Macs** (M1/M2/M3):
- Config: `/opt/homebrew/etc/mecabrc`
- Dictionary: `/opt/homebrew/lib/mecab/dic/ipadic`

**Intel Macs**:
- Config: `/usr/local/etc/mecabrc`
- Dictionary: `/usr/local/lib/mecab/dic/ipadic`

---

## ✅ After Setup

Once MeCab is configured:

1. **Kokoro TTS will work** with Japanese text
2. **You can use different voices**: `af_bella`, `af_sarah`, etc.
3. **TTS generation will be faster** than macOS native

Test with:
```bash
python scripts/test_tts_playback.py
```

---

**Last Updated**: 2025-01-07

