#!/usr/bin/env python3
"""
Simple demo of Dia TTS integration with Yukio.

This script demonstrates basic TTS functionality:
1. Loading the TTS model
2. Generating speech from text
3. Saving audio to file
4. Voice cloning (optional)

Usage:
    python3 examples/tts_demo.py
    python3 examples/tts_demo.py --verbose
    python3 examples/tts_demo.py --device cuda
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tts import TTSManager, generate_and_save


def demo_basic_usage():
    """Demo 1: Basic text-to-speech usage."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Text-to-Speech")
    print("="*60)

    # Initialize TTS
    print("Initializing TTS...")
    tts = TTSManager()

    if not tts.is_available():
        print("\n❌ TTS is not available!")
        print("\nTo enable TTS, install Dia:")
        print("  pip install git+https://github.com/nari-labs/dia.git")
        print("\nNote: Dia requires:")
        print("  - ~10GB VRAM (GPU) or CPU with patience")
        print("  - ~3GB download for model weights")
        return False

    print(f"✓ TTS loaded successfully on {tts.device}")

    # Simple greeting
    text = "[S1] Hello! I am Yukio, your Japanese tutor. Let's learn together!"

    print(f"\nGenerating speech for:")
    print(f"  '{text}'")

    audio = tts.generate_speech(text, verbose=True)

    if audio is not None:
        output_path = "yukio_data/examples/demo_basic.mp3"
        success = tts.save_audio(output_path, audio)

        if success:
            print(f"\n✓ Audio saved to: {output_path}")
            print(f"  Duration: ~{len(audio) / 44100:.1f} seconds")
            return True
        else:
            print("\n❌ Failed to save audio")
            return False
    else:
        print("\n❌ Failed to generate audio")
        return False


def demo_dialogue():
    """Demo 2: Multi-speaker dialogue."""
    print("\n" + "="*60)
    print("DEMO 2: Multi-Speaker Dialogue")
    print("="*60)

    tts = TTSManager()

    if not tts.is_available():
        print("❌ TTS not available")
        return False

    # Teacher-student dialogue
    dialogue = """
    [S1] Welcome to your first Japanese lesson!
    [S2] Thank you! I'm excited to get started.
    [S1] Great! Let's begin with basic greetings. Can you say 'hello' in Japanese?
    [S2] Hmm, let me think... (thinking) Is it 'konnichiwa'?
    [S1] Exactly right! (laughs) Very good!
    [S2] Yay! (excited)
    """.strip()

    print("\nGenerating dialogue...")
    audio = tts.generate_speech(dialogue, verbose=True)

    if audio is not None:
        output_path = "yukio_data/examples/demo_dialogue.mp3"
        tts.save_audio(output_path, audio)
        print(f"\n✓ Dialogue saved to: {output_path}")
        return True
    else:
        print("\n❌ Failed to generate dialogue")
        return False


def demo_japanese_romaji():
    """Demo 3: Japanese text using romaji."""
    print("\n" + "="*60)
    print("DEMO 3: Japanese (Romaji)")
    print("="*60)

    print("\nNote: Dia currently only supports English.")
    print("For Japanese, we use romanized text (romaji).")
    print("Native Japanese support coming in future versions!\n")

    tts = TTSManager()

    if not tts.is_available():
        print("❌ TTS not available")
        return False

    # Common Japanese phrases in romaji
    japanese_text = """
    [S1] Konnichiwa! Watashi wa Yukio desu.
    [S2] Hajimemashite! Yoroshiku onegaishimasu.
    [S1] Nihongo o benkyou shimashou!
    [S2] Hai! Ganbarimasou!
    """.strip()

    print("Generating Japanese (romaji) speech...")
    audio = tts.generate_speech(japanese_text, verbose=True)

    if audio is not None:
        output_path = "yukio_data/examples/demo_japanese.mp3"
        tts.save_audio(output_path, audio)
        print(f"\n✓ Japanese audio saved to: {output_path}")
        return True
    else:
        print("\n❌ Failed to generate Japanese audio")
        return False


def demo_caching():
    """Demo 4: Caching for faster repeated generation."""
    print("\n" + "="*60)
    print("DEMO 4: Audio Caching")
    print("="*60)

    tts = TTSManager(enable_cache=True)

    if not tts.is_available():
        print("❌ TTS not available")
        return False

    # Common phrase that might be used often
    common_phrase = "[S1] Great job! Keep practicing!"

    print("\nGenerating common phrase (first time)...")
    import time

    start = time.time()
    audio1 = tts.generate_speech(common_phrase, verbose=False)
    time1 = time.time() - start

    if audio1 is None:
        print("❌ Failed to generate audio")
        return False

    print(f"  First generation: {time1:.2f}s")

    print("\nGenerating same phrase (should use cache)...")
    start = time.time()
    audio2 = tts.generate_speech(common_phrase, verbose=False)
    time2 = time.time() - start

    print(f"  Cached generation: {time2:.2f}s")
    print(f"  Speedup: {time1/time2:.1f}x faster")

    cache_size = tts.get_cache_size()
    print(f"\n  Cache size: {cache_size / 1024:.2f} KB")

    return True


def demo_convenience_function():
    """Demo 5: Quick generation using convenience function."""
    print("\n" + "="*60)
    print("DEMO 5: Convenience Function")
    print("="*60)

    print("\nUsing generate_and_save() for one-shot generation...")

    success = generate_and_save(
        text="[S1] This is a quick and easy way to generate speech!",
        output_path="yukio_data/examples/demo_convenience.mp3",
        verbose=True
    )

    if success:
        print("\n✓ Audio generated and saved in one step")
        return True
    else:
        print("\n❌ Failed to generate audio")
        return False


def main():
    """Run all demos."""
    parser = argparse.ArgumentParser(description="Dia TTS Demo")
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--device',
        type=str,
        default=None,
        help='Device to use (cuda/cpu)'
    )
    parser.add_argument(
        '--demo',
        type=str,
        choices=['basic', 'dialogue', 'japanese', 'caching', 'convenience', 'all'],
        default='all',
        help='Which demo to run'
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("🎙️  DIA TTS INTEGRATION DEMO")
    print("="*60)
    print("\nThis demo showcases text-to-speech features in Yukio.")

    # Create output directory
    output_dir = Path("yukio_data/examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run selected demos
    demos = {
        'basic': demo_basic_usage,
        'dialogue': demo_dialogue,
        'japanese': demo_japanese_romaji,
        'caching': demo_caching,
        'convenience': demo_convenience_function
    }

    results = {}

    if args.demo == 'all':
        for name, demo_func in demos.items():
            results[name] = demo_func()
    else:
        results[args.demo] = demos[args.demo]()

    # Print summary
    print("\n" + "="*60)
    print("DEMO SUMMARY")
    print("="*60)

    for demo_name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{status:10} - {demo_name.title()}")

    print("\n" + "="*60)

    if all(results.values()):
        print("🎉 All demos completed successfully!")
        print("\nGenerated audio files are in: yukio_data/examples/")
        print("\nNext steps:")
        print("  1. Listen to the generated audio files")
        print("  2. Try modifying the text in this script")
        print("  3. Experiment with different parameters")
        print("  4. Integrate TTS into your Japanese learning workflow")
        return 0
    else:
        print("⚠️  Some demos failed. Check the output above.")
        print("\nCommon issues:")
        print("  - Dia not installed: pip install git+https://github.com/nari-labs/dia.git")
        print("  - GPU memory: Try --device cpu (slower)")
        print("  - Network: First run downloads ~3GB model")
        return 1


if __name__ == "__main__":
    sys.exit(main())
