#!/usr/bin/env python3
"""
Test different Kokoro voices to find the best one for Yukio.

Tests multiple voices and saves samples so you can compare them.
"""

import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tts import TTSManager
import time

def test_voices():
    """Test different Kokoro voices."""
    print("🎌 Testing Kokoro Voices for Yukio")
    print("=" * 60)
    
    # Voices to test (less squeaky options)
    voices_to_test = [
        ("af_bella", "Softer, gentler, more natural"),
        ("af_sarah", "Clear, professional"),
        ("af_sky", "Neutral tone"),
        ("af_heart", "Cute, high-pitched (original)"),
    ]
    
    test_text = "こんにちは、George！I am Yukio, your Japanese tutor. I will speak clearly and at a comfortable pace."
    
    print(f"\nTest text: {test_text[:50]}...")
    print(f"\nTesting {len(voices_to_test)} voices with slower speech rate (120 WPM)...")
    print()
    
    os.makedirs("./yukio_data/audio/voice_tests", exist_ok=True)
    
    for voice_name, description in voices_to_test:
        print(f"{'='*60}")
        print(f"Testing: {voice_name}")
        print(f"Description: {description}")
        print()
        
        try:
            tts = TTSManager(engine="kokoro", voice=voice_name, speech_rate=120)
            
            if tts.is_available() and tts.engine == "kokoro":
                print(f"✅ Voice {voice_name} initialized")
                
                # Generate audio
                output_path = f"./yukio_data/audio/voice_tests/{voice_name}_test.wav"
                print(f"🎤 Generating audio...")
                
                audio = tts.generate_speech(test_text, verbose=False)
                if audio is not None:
                    tts.save_audio(output_path, audio, sample_rate=24000)
                    size = os.path.getsize(output_path)
                    print(f"✅ Saved: {output_path} ({size/1024:.1f} KB)")
                    print(f"🎵 Play with: afplay {output_path}")
                else:
                    print(f"❌ Failed to generate audio")
            else:
                print(f"⚠️  Voice not available (using fallback: {tts.engine})")
        
        except Exception as e:
            print(f"❌ Error testing {voice_name}: {e}")
        
        print()
        time.sleep(1)
    
    print("=" * 60)
    print("✅ Voice testing complete!")
    print("\n📁 Test files saved in: ./yukio_data/audio/voice_tests/")
    print("\n💡 Recommendation: Listen to each file and choose the one that sounds best.")
    print("   Suggested: af_bella or af_sarah for a more natural, less squeaky voice.")

if __name__ == "__main__":
    test_voices()

