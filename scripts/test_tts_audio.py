#!/usr/bin/env python3
"""
Test TTS audio generation and playback.
"""

import requests
import os
import sys
from pathlib import Path

# Test texts
test_texts = [
    "こんにちは、George！",
    "Hello, this is a test of the text-to-speech system.",
    "日本語の音声合成をテストしています。",
    "I'm Yukio, your Japanese language tutor.",
]

def test_tts(text: str, output_file: str = None):
    """Test TTS endpoint with given text."""
    if output_file is None:
        output_file = f"/tmp/test_tts_{hash(text) % 10000}.wav"
    
    url = "http://localhost:8058/api/tts"
    
    print(f"\n🎤 Testing TTS with text: {text[:50]}...")
    print(f"   URL: {url}")
    
    try:
        response = requests.post(
            url,
            json={"text": text},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            # Save audio file
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            print(f"✅ Success! Generated {file_size:,} bytes")
            print(f"   Saved to: {output_file}")
            
            # Try to play on macOS
            if sys.platform == "darwin":
                print(f"   Playing audio...")
                os.system(f"afplay {output_file}")
                print(f"   ✅ Audio played!")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error: Backend not running at {url}")
        print(f"   Start the backend with: uvicorn agent.api:app --reload --port 8058")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🎵 TTS Audio Test")
    print("=" * 60)
    
    # Check if backend is running
    try:
        health = requests.get("http://localhost:8058/health", timeout=2)
        if health.status_code == 200:
            print("✅ Backend is running")
        else:
            print("⚠️  Backend health check failed")
    except:
        print("❌ Backend not running!")
        print("   Start it with: uvicorn agent.api:app --reload --port 8058")
        sys.exit(1)
    
    # Test each text
    results = []
    for i, text in enumerate(test_texts, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_texts)}")
        result = test_tts(text)
        results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    if passed < total:
        print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Audio is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")

