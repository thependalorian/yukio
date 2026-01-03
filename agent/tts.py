"""
Text-to-Speech (TTS) module using Dia 1.6B model.

This module provides a wrapper around the Dia text-to-speech model for
generating Japanese and English audio from text. It's designed to be optional
and non-blocking for the Yukio Japanese tutor application.

Key Features:
- Optional integration (doesn't break app if Dia is unavailable)
- GPU acceleration with CPU fallback
- Voice cloning support
- Async audio generation
- Caching for common phrases
- Japanese text support (extensible for future models)

Usage:
    from agent.tts import TTSManager

    tts = TTSManager()
    if tts.is_available():
        audio = tts.generate_speech("Hello, world!")
        tts.save_audio("output.mp3", audio)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union
import hashlib
import json

import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


class TTSManager:
    """
    Manages text-to-speech generation using Dia 1.6B model.

    This class provides a clean interface for TTS functionality with
    proper error handling, caching, and graceful degradation when
    Dia is not available.

    Attributes:
        model: Dia model instance (None if unavailable)
        is_loaded: Whether the model is successfully loaded
        device: Device to run inference on (cuda/cpu)
        cache_dir: Directory for caching generated audio
        compute_dtype: Precision for inference (float16/float32)
    """

    def __init__(
        self,
        model_name: str = "nari-labs/Dia-1.6B",
        device: Optional[str] = None,
        compute_dtype: str = "float16",
        enable_cache: bool = True,
        cache_dir: str = "./yukio_data/tts_cache"
    ):
        """
        Initialize the TTS manager.

        Args:
            model_name: HuggingFace model ID or local path
            device: Device to use ('cuda', 'cpu', or None for auto)
            compute_dtype: Compute precision ('float16', 'float32', 'bfloat16')
            enable_cache: Whether to cache generated audio
            cache_dir: Directory for audio cache
        """
        self.model_name = model_name
        self.device = device
        self.compute_dtype = compute_dtype
        self.enable_cache = enable_cache
        self.cache_dir = Path(cache_dir)

        self.model = None
        self.is_loaded = False

        # Create cache directory if caching is enabled
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache_index()

        # Try to load the model
        self._load_model()

    def _load_model(self) -> None:
        """
        Load the Dia model.

        This method attempts to import and load the Dia model. If Dia is not
        installed or if there's an error loading the model, it logs the error
        and sets is_loaded to False, allowing the app to continue without TTS.
        """
        try:
            # Try to import Dia from local installation
            # Reason: We have Dia in yukio/dia directory, add it to sys.path
            dia_path = Path(__file__).parent.parent / "dia"
            if dia_path.exists():
                # Add the dia directory to Python path if not already there
                dia_path_str = str(dia_path.absolute())
                if dia_path_str not in sys.path:
                    sys.path.insert(0, dia_path_str)
                    logger.info(f"Added local Dia path to sys.path: {dia_path_str}")
            else:
                logger.warning(f"Local Dia directory not found at: {dia_path}")

            from dia.model import Dia

            logger.info(f"Loading Dia model: {self.model_name}")

            # Determine device (prioritize GPU: CUDA > CPU > MPS)
            # Note: MPS has limitations with Dia model (65536 channel limit), so we prefer CPU on Mac
            import torch
            if self.device is None:
                if torch.cuda.is_available():
                    self.device = "cuda"
                    logger.info("Using CUDA for TTS")
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    # MPS has issues with Dia model - use CPU instead for reliability
                    self.device = "cpu"
                    logger.info("MPS available but using CPU for TTS (MPS has limitations with Dia model)")
                else:
                    self.device = "cpu"
                    logger.info("Using CPU for TTS")

            # Load model
            # Note: Dia.from_pretrained accepts device as torch.device or None
            device_obj = torch.device(self.device) if self.device else None
            self.model = Dia.from_pretrained(
                self.model_name,
                compute_dtype=self.compute_dtype,
                device=device_obj
            )

            self.is_loaded = True
            logger.info("Dia model loaded successfully")

        except ImportError as e:
            logger.warning(f"Dia TTS not available: {e}")
            if dia_path.exists():
                logger.warning(f"Local Dia found at {dia_path}, but dependencies are missing.")
                logger.warning("Install dependencies: cd dia && pip install -e .")
                logger.warning("Or install: pip install descript-audio-codec torch torchaudio")
            else:
                logger.warning("Install Dia to enable text-to-speech features")
            self.is_loaded = False
        except Exception as e:
            logger.error(f"Failed to load Dia model: {e}")
            self.is_loaded = False

    def is_available(self) -> bool:
        """
        Check if TTS is available.

        Returns:
            True if the model is loaded and ready, False otherwise
        """
        return self.is_loaded and self.model is not None

    def _load_cache_index(self) -> None:
        """Load the cache index from disk."""
        self.cache_index_file = self.cache_dir / "cache_index.json"
        if self.cache_index_file.exists():
            try:
                with open(self.cache_index_file, 'r') as f:
                    self.cache_index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self.cache_index = {}
        else:
            self.cache_index = {}

    def _save_cache_index(self) -> None:
        """Save the cache index to disk."""
        try:
            with open(self.cache_index_file, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")

    def _get_cache_key(self, text: str, **kwargs) -> str:
        """
        Generate a cache key for the given text and parameters.

        Args:
            text: Input text
            **kwargs: Additional parameters (temperature, cfg_scale, etc.)

        Returns:
            MD5 hash of the text and parameters
        """
        # Create a deterministic string from text and parameters
        cache_string = text + json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_cached_audio(self, cache_key: str) -> Optional[np.ndarray]:
        """
        Retrieve cached audio if available.

        Args:
            cache_key: Cache key for the audio

        Returns:
            Cached audio array or None if not found
        """
        if not self.enable_cache:
            return None

        if cache_key in self.cache_index:
            cache_file = self.cache_dir / f"{cache_key}.npy"
            if cache_file.exists():
                try:
                    audio = np.load(cache_file)
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return audio
                except Exception as e:
                    logger.warning(f"Failed to load cached audio: {e}")

        return None

    def _cache_audio(self, cache_key: str, audio: np.ndarray, text: str) -> None:
        """
        Cache generated audio.

        Args:
            cache_key: Cache key
            audio: Audio array to cache
            text: Original text (for reference)
        """
        if not self.enable_cache:
            return

        try:
            cache_file = self.cache_dir / f"{cache_key}.npy"
            np.save(cache_file, audio)

            # Update index
            self.cache_index[cache_key] = {
                'text': text[:100],  # Store first 100 chars for reference
                'file': str(cache_file)
            }
            self._save_cache_index()

            logger.debug(f"Cached audio for key: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache audio: {e}")

    def generate_speech(
        self,
        text: str,
        max_tokens: Optional[int] = None,
        cfg_scale: float = 3.0,
        temperature: float = 1.3,
        top_p: float = 0.95,
        use_torch_compile: bool = False,
        audio_prompt: Optional[Union[str, np.ndarray]] = None,
        use_cache: bool = True,
        verbose: bool = False
    ) -> Optional[np.ndarray]:
        """
        Generate speech from text using Dia model.
        
        Note: On Mac M1/M2 (MPS), we limit max_tokens to avoid MPS limitations.
        For longer text, consider splitting into shorter segments.
        """
        """
        Generate speech from text.

        Args:
            text: Input text to convert to speech
                Format: "[S1] Speaker 1 text [S2] Speaker 2 text"
                For single speaker: Just use regular text or "[S1] text"
            max_tokens: Maximum audio tokens to generate
            cfg_scale: Classifier-free guidance scale
            temperature: Sampling temperature (higher = more random)
            top_p: Nucleus sampling probability
            use_torch_compile: Use torch.compile for faster inference
            audio_prompt: Optional audio prompt for voice cloning
            use_cache: Whether to use cached audio if available
            verbose: Print generation progress

        Returns:
            Audio array (numpy) or None if generation failed

        Note:
            Currently Dia only supports English. Japanese support is
            planned for future versions. For now, this will work with
            romanized Japanese (romaji) or English translations.
        """
        if not self.is_available():
            logger.warning("TTS not available - cannot generate speech")
            return None

        # Check cache first
        if use_cache:
            cache_params = {
                'cfg_scale': cfg_scale,
                'temperature': temperature,
                'top_p': top_p,
                'max_tokens': max_tokens
            }
            cache_key = self._get_cache_key(text, **cache_params)
            cached_audio = self._get_cached_audio(cache_key)
            if cached_audio is not None:
                return cached_audio

        try:
            if verbose:
                logger.info(f"Generating speech for: {text[:50]}...")

            # Limit max_tokens for reasonable generation time
            # CPU is slower but more reliable than MPS for Dia model
            # Limit to ~800 tokens for faster generation (roughly 15-20 seconds of audio)
            if max_tokens is None or max_tokens > 800:
                max_tokens = 800
                if verbose:
                    logger.info(f"Limiting max_tokens to {max_tokens} for faster generation")

            # Generate audio with error handling for MPS
            try:
                audio = self.model.generate(
                    text=text,
                    max_tokens=max_tokens,
                    cfg_scale=cfg_scale,
                    temperature=temperature,
                    top_p=top_p,
                    use_torch_compile=use_torch_compile,
                    audio_prompt=audio_prompt,
                    verbose=verbose
                )
            except RuntimeError as e:
                if "MPS" in str(e) or "65536" in str(e):
                    logger.warning(f"MPS error detected: {e}")
                    logger.warning("MPS has limitations on Mac. Consider using shorter text or disabling voice.")
                    return None
                else:
                    raise

            # Cache the result
            if use_cache and audio is not None:
                self._cache_audio(cache_key, audio, text)

            return audio

        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return None

    def save_audio(
        self,
        path: str,
        audio: np.ndarray,
        sample_rate: int = 44100
    ) -> bool:
        """
        Save audio to file.

        Args:
            path: Output file path (supports .wav, .mp3, .ogg, etc.)
            audio: Audio array from generate_speech()
            sample_rate: Audio sample rate (default: 44100)

        Returns:
            True if successful, False otherwise
        """
        if audio is None:
            logger.warning("Cannot save None audio")
            return False

        try:
            # Ensure output directory exists
            output_path = Path(path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Use Dia's save method if available
            if self.model is not None:
                self.model.save_audio(str(path), audio)
            else:
                # Fallback to soundfile
                import soundfile as sf
                sf.write(path, audio, sample_rate)

            logger.info(f"Saved audio to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False

    def load_audio_prompt(self, audio_path: str):
        """
        Load an audio file to use as a voice cloning prompt.

        Args:
            audio_path: Path to audio file (.wav, .mp3, etc.)

        Returns:
            Encoded audio tensor or None if loading failed
        """
        if not self.is_available():
            logger.warning("TTS not available - cannot load audio prompt")
            return None

        try:
            return self.model.load_audio(audio_path)
        except Exception as e:
            logger.error(f"Failed to load audio prompt: {e}")
            return None

    def clear_cache(self) -> None:
        """Clear the TTS cache."""
        if not self.enable_cache:
            return

        try:
            # Remove all cached audio files
            for cache_file in self.cache_dir.glob("*.npy"):
                cache_file.unlink()

            # Clear index
            self.cache_index = {}
            self._save_cache_index()

            logger.info("TTS cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    def get_cache_size(self) -> int:
        """
        Get the size of the TTS cache in bytes.

        Returns:
            Total size of cached files in bytes
        """
        if not self.enable_cache:
            return 0

        total_size = 0
        for cache_file in self.cache_dir.glob("*.npy"):
            total_size += cache_file.stat().st_size

        return total_size

    def format_japanese_text(self, japanese_text: str, speaker: str = "S1") -> str:
        """
        Formats Japanese text for TTS by converting it to Romaji using pykakasi.

        Since Dia currently only supports English, this method converts
        Japanese text (hiragana, katakana, kanji) to Romaji.

        Args:
            japanese_text: Japanese text to convert
            speaker: Speaker ID (S1 or S2)

        Returns:
            Formatted Romaji text for Dia, or an empty string if conversion fails.
        """
        # Attempt to import pykakasi, as it's an optional dependency for TTS
        try:
            import pykakasi
        except ImportError:
            logger.warning("pykakasi not installed. Cannot convert Japanese to Romaji for TTS.")
            logger.warning("Please install it: pip install pykakasi")
            # Fallback to original text, which will likely fail in TTS
            return f"[{speaker}] {japanese_text}"

        try:
            kks = pykakasi.kakasi()
            result = kks.convert(japanese_text)
            # The result is a list of dicts, e.g., [{'orig': '日本語', 'hira': 'にほんご', 'kana': 'ニホンゴ', 'romaji': 'nihongo'}]
            # We join the 'romaji' parts with spaces for better pronunciation by the TTS model.
            romaji_text = " ".join([item['romaji'] for item in result])
            return f"[{speaker}] {romaji_text}"
        except Exception as e:
            logger.error(f"Failed to convert Japanese text to Romaji: {e}")
            # Fallback to the original text if conversion fails
            return f"[{speaker}] {japanese_text}"

    def __repr__(self) -> str:
        """String representation of TTSManager."""
        status = "available" if self.is_available() else "unavailable"
        return f"TTSManager(model={self.model_name}, device={self.device}, status={status})"


# Convenience functions for quick usage

def create_tts_manager(
    enable_tts: bool = True,
    device: Optional[str] = None
) -> TTSManager:
    """
    Create a TTS manager instance with sensible defaults.

    Args:
        enable_tts: Whether to enable TTS (from config/env)
        device: Device to use (None for auto-detect)

    Returns:
        TTSManager instance
    """
    if not enable_tts:
        logger.info("TTS disabled by configuration")

    return TTSManager(device=device)


def generate_and_save(
    text: str,
    output_path: str,
    tts_manager: Optional[TTSManager] = None,
    **kwargs
) -> bool:
    """
    Generate speech and save to file in one step.

    Args:
        text: Text to convert to speech
        output_path: Output audio file path
        tts_manager: Existing TTS manager (creates one if None)
        **kwargs: Additional arguments for generate_speech()

    Returns:
        True if successful, False otherwise
    """
    if tts_manager is None:
        tts_manager = TTSManager()

    if not tts_manager.is_available():
        logger.warning("TTS not available")
        return False

    audio = tts_manager.generate_speech(text, **kwargs)
    if audio is not None:
        return tts_manager.save_audio(output_path, audio)

    return False
