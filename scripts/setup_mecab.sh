#!/bin/bash
# Setup script to fix MeCab configuration path for Kokoro TTS
# This creates a symlink so fugashi can find the mecabrc file

set -e

echo "🔧 MeCab Configuration Setup"
echo "=" | head -c 60 && echo ""

# Check if running on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "⚠️  This script is for macOS only"
    exit 1
fi

# Find MeCab config file
MECABRC_SOURCE=""
if [[ -f "/opt/homebrew/etc/mecabrc" ]]; then
    MECABRC_SOURCE="/opt/homebrew/etc/mecabrc"
    echo "✅ Found MeCab config: $MECABRC_SOURCE (Apple Silicon)"
elif [[ -f "/usr/local/etc/mecabrc" ]]; then
    MECABRC_SOURCE="/usr/local/etc/mecabrc"
    echo "✅ Found MeCab config: $MECABRC_SOURCE (Intel)"
else
    echo "❌ MeCab config not found. Install MeCab first:"
    echo "   brew install mecab mecab-ipadic"
    exit 1
fi

# Target location (where fugashi expects it)
MECABRC_TARGET="/usr/local/etc/mecabrc"
MECABRC_DIR="/usr/local/etc"

# Check if target already exists
if [[ -f "$MECABRC_TARGET" ]]; then
    if [[ -L "$MECABRC_TARGET" ]]; then
        CURRENT_LINK=$(readlink "$MECABRC_TARGET")
        if [[ "$CURRENT_LINK" == "$MECABRC_SOURCE" ]]; then
            echo "✅ Symlink already exists and points to correct file"
            echo "   $MECABRC_TARGET -> $MECABRC_SOURCE"
            exit 0
        else
            echo "⚠️  Symlink exists but points to different file:"
            echo "   Current: $MECABRC_TARGET -> $CURRENT_LINK"
            echo "   Expected: $MECABRC_TARGET -> $MECABRC_SOURCE"
            read -p "Replace it? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Cancelled"
                exit 1
            fi
            sudo rm "$MECABRC_TARGET"
        fi
    else
        echo "⚠️  File exists at $MECABRC_TARGET (not a symlink)"
        read -p "Backup and replace? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cancelled"
            exit 1
        fi
        sudo mv "$MECABRC_TARGET" "${MECABRC_TARGET}.backup"
    fi
fi

# Create directory if needed
if [[ ! -d "$MECABRC_DIR" ]]; then
    echo "📁 Creating directory: $MECABRC_DIR"
    sudo mkdir -p "$MECABRC_DIR"
fi

# Create symlink
echo "🔗 Creating symlink..."
echo "   $MECABRC_TARGET -> $MECABRC_SOURCE"
sudo ln -sf "$MECABRC_SOURCE" "$MECABRC_TARGET"

# Verify
if [[ -L "$MECABRC_TARGET" ]] && [[ "$(readlink "$MECABRC_TARGET")" == "$MECABRC_SOURCE" ]]; then
    echo ""
    echo "✅ SUCCESS! MeCab configuration is now set up."
    echo ""
    echo "📋 Verification:"
    ls -la "$MECABRC_TARGET"
    echo ""
    echo "🎌 Kokoro TTS should now work properly!"
    echo ""
    echo "Test it with:"
    echo "   python -c \"from kokoro import KPipeline; p = KPipeline(lang_code='j'); print('✅ Kokoro ready!')\""
else
    echo "❌ Failed to create symlink"
    exit 1
fi

