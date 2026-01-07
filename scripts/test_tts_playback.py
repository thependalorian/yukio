#!/usr/bin/env python3
"""
Test script for TTS generation and automatic playback.

This script tests the complete flow:
1. Generate TTS from text response
2. Save to tts_output.wav
3. Play the audio automatically
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tts import TTSManager
import os

def test_tts_generation_and_playback():
    """Test TTS generation, saving, and playback."""
    print("🎌 Testing TTS Generation and Playback")
    print("=" * 60)
    
    # Initialize TTS manager
    print("\n1️⃣ Initializing TTS Manager...")
    tts = TTSManager(speech_rate=160)
    
    if not tts.is_available():
        print("❌ TTS not available")
        return False
    
    print(f"✅ TTS initialized")
    print(f"   Engine: {tts.engine}")
    print(f"   Voice: {tts.voice if hasattr(tts, 'voice') else 'default'}")
    print(f"   Rate: {tts.speech_rate} WPM")
    
    # Test text (simulating a Yukio response)
    test_responses = [
        "こんにちは、George！I am Yukio, your Japanese tutor.",
        "今日は何を勉強したいですか？What would you like to learn today?",
        "Great job! You're making excellent progress with your Japanese studies."
    ]
    
    for i, text in enumerate(test_responses, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_responses)}")
        print(f"Text: {text[:50]}...")
        print()
        
        # Generate, save, and play
        output_path = "./yukio_data/audio/tts_output.wav"
        os.makedirs("./yukio_data/audio", exist_ok=True)
        
        print("2️⃣ Generating TTS audio...")
        success = tts.generate_and_play(
            text=text,
            output_path=output_path,
            auto_play=True,
            speech_rate=160
        )
        
        if success:
            print(f"✅ Success! Audio generated and played")
            print(f"   File: {output_path}")
            
            # Check file exists
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                print(f"   Size: {size/1024:.1f} KB")
            
            # Wait a bit between tests
            if i < len(test_responses):
                print("\n⏳ Waiting 2 seconds before next test...")
                import time
                time.sleep(2)
        else:
            print("❌ Failed to generate/play audio")
            return False
    
    print(f"\n{'='*60}")
    print("✅ All tests passed!")
    print(f"\n📁 Final audio file: ./yukio_data/audio/tts_output.wav")
    print("🎵 You can play it again with: afplay ./yukio_data/audio/tts_output.wav")
    
    return True

if __name__ == "__main__":
    try:
        success = test_tts_generation_and_playback()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

