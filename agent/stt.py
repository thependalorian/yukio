"""
Speech-to-Text (STT) module for pronunciation practice.

This module provides STT functionality using Whisper for local speech recognition
and pronunciation analysis for Japanese language learning.

Key Features:
- Local Whisper-based STT (privacy-focused)
- Japanese speech recognition
- Pronunciation scoring and feedback
- Sound-by-sound analysis

Usage:
    from agent.stt import STTManager
    
    stt = STTManager()
    if stt.is_available():
        transcript, score, feedback = stt.analyze_pronunciation(
            audio_file="recording.wav",
            target_text="こんにちは",
            target_romaji="konnichiwa"
        )
"""

import logging
import os
import platform
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

# Try to import Whisper (optional)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    whisper = None
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available. Install with: pip install openai-whisper")

# Try to import pykakasi for romaji conversion
try:
    import pykakasi
    KAKASI_AVAILABLE = True
except ImportError:
    pykakasi = None
    KAKASI_AVAILABLE = False
    logger.warning("pykakasi not available. Install with: pip install pykakasi")


class STTManager:
    """
    Manages speech-to-text conversion and pronunciation analysis.
    
    Uses Whisper for local speech recognition, ensuring privacy and
    offline capability (aligned with Yukio's local-first philosophy).
    """
    
    def __init__(
        self,
        model_size: str = "base",
        language: str = "ja"
    ):
        """
        Initialize the STT manager.
        
        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
                      Smaller = faster, less accurate. Larger = slower, more accurate.
                      Default "base" is a good balance.
            language: Language code ("ja" for Japanese, "en" for English, etc.)
        """
        self.model_size = model_size
        self.language = language
        self.whisper_model = None
        self.kakasi = None
        self.is_loaded = False
        
        # Initialize components
        if WHISPER_AVAILABLE:
            self._init_whisper()
        else:
            logger.warning("Whisper not available. STT features disabled.")
        
        if KAKASI_AVAILABLE:
            try:
                self.kakasi = pykakasi.kakasi()
                self.kakasi.setMode("H", "a")  # Hiragana to romaji
                self.kakasi.setMode("K", "a")  # Katakana to romaji
                self.kakasi.setMode("J", "a")  # Kanji to romaji
                self.kakasi.setMode("r", "Hepburn")  # Use Hepburn romanization
                self.converter = self.kakasi.getConverter()
            except Exception as e:
                logger.warning(f"Failed to initialize pykakasi: {e}")
                self.kakasi = None
    
    def _init_whisper(self):
        """Initialize Whisper model."""
        try:
            logger.info(f"Loading Whisper model: {self.model_size}")
            self.whisper_model = whisper.load_model(self.model_size)
            self.is_loaded = True
            logger.info(f"✅ Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self.is_loaded = False
    
    def is_available(self) -> bool:
        """
        Check if STT is available.
        
        Returns:
            True if Whisper is loaded and ready, False otherwise
        """
        return self.is_loaded and self.whisper_model is not None
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file (supports .wav, .mp3, .m4a, etc.)
            language: Language code (defaults to self.language)
            
        Returns:
            Transcribed text
        """
        if not self.is_available():
            raise RuntimeError("Whisper not available. Install with: pip install openai-whisper")
        
        try:
            lang = language or self.language
            result = self.whisper_model.transcribe(
                audio_path,
                language=lang,
                task="transcribe"
            )
            transcript = result["text"].strip()
            logger.debug(f"Transcribed: {transcript}")
            return transcript
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_audio_data(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio data (numpy array) to text.
        
        Args:
            audio_data: Audio data as numpy array (mono, float32)
            sample_rate: Sample rate of audio (default: 16000)
            language: Language code (defaults to self.language)
            
        Returns:
            Transcribed text
        """
        if not self.is_available():
            raise RuntimeError("Whisper not available")
        
        try:
            import tempfile
            import soundfile as sf
            
            # Save to temporary file (Whisper expects file path)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                sf.write(tmp_path, audio_data, sample_rate)
            
            try:
                transcript = self.transcribe(tmp_path, language=language)
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
            
            return transcript
        except Exception as e:
            logger.error(f"Audio data transcription failed: {e}")
            raise
    
    def _japanese_to_romaji(self, text: str) -> str:
        """
        Convert Japanese text to romaji.
        
        Args:
            text: Japanese text (hiragana, katakana, kanji)
            
        Returns:
            Romaji representation
        """
        if not self.kakasi:
            # Fallback: return as-is if pykakasi not available
            logger.warning("pykakasi not available, cannot convert to romaji")
            return text
        
        try:
            result = self.converter.do(text)
            return result.strip()
        except Exception as e:
            logger.warning(f"Romaji conversion failed: {e}")
            return text
    
    def _calculate_pronunciation_score(
        self,
        transcribed_text: str,
        target_text: str,
        target_romaji: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        Calculate pronunciation score and generate feedback.
        
        Args:
            transcribed_text: Text transcribed from user's audio
            target_text: Target Japanese text
            target_romaji: Target romaji (optional, will be generated if not provided)
            
        Returns:
            Tuple of (score: int 0-100, feedback: str)
        """
        # Normalize texts (remove punctuation, lowercase for romaji comparison)
        transcribed_clean = transcribed_text.strip().lower()
        
        # Convert target to romaji if not provided
        if target_romaji:
            target_romaji_clean = target_romaji.strip().lower()
        else:
            target_romaji_clean = self._japanese_to_romaji(target_text).strip().lower()
        
        # Simple scoring algorithm:
        # 1. Exact match = 100%
        # 2. Character-level similarity for Japanese text
        # 3. Word-level similarity for romaji
        
        # Check exact match first
        if transcribed_clean == target_romaji_clean:
            return 100, "Perfect pronunciation! 🎉"
        
        # Calculate character-level similarity for Japanese
        target_jp_chars = set(target_text.replace(" ", ""))
        transcribed_jp_chars = set(transcribed_text.replace(" ", ""))
        
        # Calculate romaji word-level similarity
        target_words = set(target_romaji_clean.split())
        transcribed_words = set(transcribed_clean.split())
        
        # Word match score (60% weight)
        if target_words:
            word_match_ratio = len(transcribed_words & target_words) / len(target_words)
        else:
            word_match_ratio = 0.0
        
        # Character match score (40% weight)
        if target_jp_chars:
            char_match_ratio = len(transcribed_jp_chars & target_jp_chars) / len(target_jp_chars)
        else:
            char_match_ratio = 0.0
        
        # Combined score
        score = int((word_match_ratio * 0.6 + char_match_ratio * 0.4) * 100)
        score = max(0, min(100, score))  # Clamp to 0-100
        
        # Generate feedback
        if score >= 90:
            feedback = "Excellent pronunciation! Very close to native."
        elif score >= 80:
            feedback = "Good pronunciation! Minor improvements needed."
        elif score >= 70:
            feedback = "Decent pronunciation. Practice the sounds more carefully."
        elif score >= 60:
            feedback = "Pronunciation needs work. Listen to the native audio and try again."
        else:
            feedback = "Pronunciation needs significant improvement. Focus on each syllable."
        
        # Add specific feedback
        missing_words = target_words - transcribed_words
        if missing_words:
            feedback += f" Missing words: {', '.join(missing_words)}"
        
        return score, feedback
    
    def analyze_pronunciation(
        self,
        audio_path: Optional[str] = None,
        audio_data: Optional[np.ndarray] = None,
        sample_rate: int = 16000,
        target_text: str = "",
        target_romaji: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze pronunciation of recorded audio.
        
        Args:
            audio_path: Path to audio file (if provided)
            audio_data: Audio data as numpy array (if provided instead of path)
            sample_rate: Sample rate of audio data (default: 16000)
            target_text: Target Japanese text to compare against
            target_romaji: Target romaji (optional, will be generated if not provided)
            
        Returns:
            Dictionary with:
            - transcript: Transcribed text
            - score: Pronunciation score (0-100)
            - feedback: Feedback message
            - target_text: Original target text
            - target_romaji: Target romaji used for comparison
        """
        if not self.is_available():
            raise RuntimeError("STT not available. Install Whisper: pip install openai-whisper")
        
        if not target_text:
            raise ValueError("target_text is required")
        
        try:
            # Transcribe audio
            if audio_path:
                transcript = self.transcribe(audio_path)
            elif audio_data is not None:
                transcript = self.transcribe_audio_data(audio_data, sample_rate)
            else:
                raise ValueError("Either audio_path or audio_data must be provided")
            
            # Calculate score and feedback
            score, feedback = self._calculate_pronunciation_score(
                transcript,
                target_text,
                target_romaji
            )
            
            # Generate target romaji if not provided
            if not target_romaji:
                target_romaji = self._japanese_to_romaji(target_text)
            
            return {
                "transcript": transcript,
                "score": score,
                "feedback": feedback,
                "target_text": target_text,
                "target_romaji": target_romaji,
                "transcribed_romaji": self._japanese_to_romaji(transcript) if transcript else ""
            }
        except Exception as e:
            logger.error(f"Pronunciation analysis failed: {e}")
            raise


# Convenience function
def create_stt_manager(model_size: str = "base") -> STTManager:
    """
    Create an STT manager instance with sensible defaults.
    
    Args:
        model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
    
    Returns:
        STTManager instance
    """
    return STTManager(model_size=model_size)

