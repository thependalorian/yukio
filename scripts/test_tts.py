#!/usr/bin/env python3
"""
Test script for Dia TTS integration with Yukio.

This script tests the TTS module with various inputs to verify:
1. Model loading
2. Basic text-to-speech generation
3. Voice cloning (if audio prompt provided)
4. Caching functionality
5. Error handling

Usage:
    python3 scripts/test_tts.py
    python3 scripts/test_tts.py --verbose
    python3 scripts/test_tts.py --no-cache
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path to import agent module
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tts import TTSManager, generate_and_save

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_model_loading():
    """Test 1: Verify model can be loaded."""
    print("\n" + "="*60)
    print("TEST 1: Model Loading")
    print("="*60)

    tts = TTSManager()

    if tts.is_available():
        print("✓ TTS model loaded successfully")
        print(f"  - Device: {tts.device}")
        print(f"  - Compute dtype: {tts.compute_dtype}")
        print(f"  - Model: {tts.model_name}")
        return tts
    else:
        print("✗ TTS model not available")
        print("\nPossible reasons:")
        print("  1. Dia not installed (pip install git+https://github.com/nari-labs/dia.git)")
        print("  2. GPU/CUDA not available (Dia requires significant compute)")
        print("  3. Model download failed")
        return None


def test_basic_generation(tts: TTSManager, verbose: bool = False):
    """Test 2: Basic text-to-speech generation."""
    print("\n" + "="*60)
    print("TEST 2: Basic Speech Generation")
    print("="*60)

    if not tts or not tts.is_available():
        print("✗ Skipping - TTS not available")
        return False

    test_text = "[S1] Hello! This is a test of the Dia text to speech model."

    print(f"Input text: {test_text}")
    print("Generating audio...")

    try:
        audio = tts.generate_speech(
            text=test_text,
            temperature=1.3,
            cfg_scale=3.0,
            verbose=verbose
        )

        if audio is not None:
            print(f"✓ Audio generated successfully")
            print(f"  - Shape: {audio.shape}")
            print(f"  - Duration: ~{len(audio) / 44100:.2f} seconds")

            # Save the audio
            output_path = "yukio_data/test_outputs/basic_test.mp3"
            success = tts.save_audio(output_path, audio)

            if success:
                print(f"  - Saved to: {output_path}")
            return True
        else:
            print("✗ Audio generation returned None")
            return False

    except Exception as e:
        print(f"✗ Error during generation: {e}")
        return False


def test_dialogue_generation(tts: TTSManager, verbose: bool = False):
    """Test 3: Multi-speaker dialogue generation."""
    print("\n" + "="*60)
    print("TEST 3: Dialogue Generation")
    print("="*60)

    if not tts or not tts.is_available():
        print("✗ Skipping - TTS not available")
        return False

    dialogue_text = (
        "[S1] Welcome to Yukio, your Japanese tutor! "
        "[S2] Thank you! I'm excited to learn Japanese. "
        "[S1] Let's start with some basic vocabulary. "
        "[S2] Sounds great! (laughs)"
    )

    print(f"Input dialogue: {dialogue_text[:80]}...")
    print("Generating dialogue audio...")

    try:
        audio = tts.generate_speech(
            text=dialogue_text,
            temperature=1.3,
            cfg_scale=3.0,
            verbose=verbose
        )

        if audio is not None:
            print(f"✓ Dialogue audio generated successfully")
            print(f"  - Duration: ~{len(audio) / 44100:.2f} seconds")

            # Save the audio
            output_path = "yukio_data/test_outputs/dialogue_test.mp3"
            success = tts.save_audio(output_path, audio)

            if success:
                print(f"  - Saved to: {output_path}")
            return True
        else:
            print("✗ Dialogue generation returned None")
            return False

    except Exception as e:
        print(f"✗ Error during dialogue generation: {e}")
        return False


def test_japanese_text(tts: TTSManager, verbose: bool = False):
    """Test 4: Japanese text formatting (English for now)."""
    print("\n" + "="*60)
    print("TEST 4: Japanese Text (Romaji)")
    print("="*60)

    if not tts or not tts.is_available():
        print("✗ Skipping - TTS not available")
        return False

    # Note: Dia currently only supports English, so we use romaji
    japanese_text = "[S1] Konnichiwa! Watashi wa Yukio desu."

    print(f"Input (romaji): {japanese_text}")
    print("Note: Dia currently only supports English.")
    print("For now, we use romanized Japanese (romaji).")
    print("Native Japanese support coming in future versions!")
    print("\nGenerating audio...")

    try:
        audio = tts.generate_speech(
            text=japanese_text,
            temperature=1.3,
            verbose=verbose
        )

        if audio is not None:
            print(f"✓ Audio generated for romaji text")

            # Save the audio
            output_path = "yukio_data/test_outputs/japanese_test.mp3"
            success = tts.save_audio(output_path, audio)

            if success:
                print(f"  - Saved to: {output_path}")
            return True
        else:
            print("✗ Audio generation returned None")
            return False

    except Exception as e:
        print(f"✗ Error during Japanese text generation: {e}")
        return False


def test_caching(tts: TTSManager):
    """Test 5: Audio caching functionality."""
    print("\n" + "="*60)
    print("TEST 5: Caching")
    print("="*60)

    if not tts or not tts.is_available():
        print("✗ Skipping - TTS not available")
        return False

    if not tts.enable_cache:
        print("✗ Caching is disabled")
        return False

    test_text = "[S1] This is a cache test. Cache me!"

    print("Generating audio (first time - should cache)...")
    import time
    start = time.time()
    audio1 = tts.generate_speech(test_text, use_cache=True)
    time1 = time.time() - start

    if audio1 is None:
        print("✗ First generation failed")
        return False

    print(f"  - First generation: {time1:.2f}s")

    print("Generating same audio (should hit cache)...")
    start = time.time()
    audio2 = tts.generate_speech(test_text, use_cache=True)
    time2 = time.time() - start

    if audio2 is None:
        print("✗ Second generation failed")
        return False

    print(f"  - Second generation: {time2:.2f}s")

    if time2 < time1 * 0.5:  # Should be significantly faster
        print(f"✓ Cache is working! Speedup: {time1/time2:.1f}x")
        cache_size = tts.get_cache_size()
        print(f"  - Cache size: {cache_size / 1024:.2f} KB")
        return True
    else:
        print("⚠ Cache might not be working (no speedup detected)")
        return False


def test_error_handling(tts: TTSManager):
    """Test 6: Error handling and edge cases."""
    print("\n" + "="*60)
    print("TEST 6: Error Handling")
    print("="*60)

    if not tts or not tts.is_available():
        print("✗ Skipping - TTS not available")
        return False

    # Test 1: Empty text
    print("Test 6.1: Empty text...")
    audio = tts.generate_speech("")
    if audio is None:
        print("  ✓ Properly handled empty text")
    else:
        print("  ⚠ Empty text generated audio (unexpected)")

    # Test 2: Very long text
    print("Test 6.2: Very long text...")
    long_text = "[S1] " + " ".join(["word"] * 1000)
    audio = tts.generate_speech(long_text, max_tokens=100)
    if audio is not None:
        print("  ✓ Handled long text with max_tokens limit")
    else:
        print("  ⚠ Long text generation failed")

    # Test 3: Invalid save path
    print("Test 6.3: Invalid save path...")
    test_audio = tts.generate_speech("[S1] Test")
    if test_audio is not None:
        success = tts.save_audio("/invalid/path/test.mp3", test_audio)
        if not success:
            print("  ✓ Properly handled invalid save path")
        else:
            print("  ⚠ Invalid path didn't fail (unexpected)")

    print("\n✓ Error handling tests completed")
    return True


def main():
    """Run all TTS tests."""
    parser = argparse.ArgumentParser(description="Test Dia TTS integration")
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output during generation'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching for tests'
    )
    parser.add_argument(
        '--device',
        type=str,
        default=None,
        help='Device to use (cuda/cpu, default: auto)'
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("DIA TTS INTEGRATION TEST SUITE")
    print("="*60)
    print("\nThis will test the Dia text-to-speech integration with Yukio.")
    print("Make sure you have:")
    print("  1. Installed Dia (pip install git+https://github.com/nari-labs/dia.git)")
    print("  2. Sufficient GPU memory (~10GB VRAM) or patience for CPU")
    print("  3. Good internet connection for model download (first run)")

    # Create output directory
    output_dir = Path("yukio_data/test_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run tests
    results = {}

    # Test 1: Model loading
    tts = test_model_loading()
    results['model_loading'] = tts is not None

    if tts and not args.no_cache:
        tts.enable_cache = True

    # Test 2: Basic generation
    if tts:
        results['basic_generation'] = test_basic_generation(tts, args.verbose)

        # Test 3: Dialogue
        results['dialogue_generation'] = test_dialogue_generation(tts, args.verbose)

        # Test 4: Japanese (romaji)
        results['japanese_text'] = test_japanese_text(tts, args.verbose)

        # Test 5: Caching
        if not args.no_cache:
            results['caching'] = test_caching(tts)

        # Test 6: Error handling
        results['error_handling'] = test_error_handling(tts)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} - {test_name.replace('_', ' ').title()}")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! TTS integration is working correctly.")
        return 0
    elif passed_tests > 0:
        print("\n⚠ Some tests passed. TTS integration is partially working.")
        return 1
    else:
        print("\n✗ All tests failed. TTS integration needs attention.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
