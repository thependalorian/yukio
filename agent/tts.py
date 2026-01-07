"""
Text-to-Speech (TTS) module supporting multiple engines.

This module provides TTS functionality with support for:
1. macOS native 'say' command (fast, lightweight)
2. Kokoro TTS (anime-style Japanese voices, requires kokoro package)

Key Features:
- Native macOS TTS (fast, no model downloads)
- Kokoro TTS (anime-style voices, high quality)
- Japanese voice support
- Audio caching for common phrases
- Automatic fallback between engines

Usage:
    from agent.tts import TTSManager

    # Use macOS native (default)
    tts = TTSManager()
    
    # Use Kokoro for anime-style voice
    tts = TTSManager(engine="kokoro", voice="af_heart")
    
    if tts.is_available():
        audio = tts.generate_speech("こんにちは")
        tts.save_audio("output.wav", audio)
"""

import logging
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Literal
import hashlib
import json

import numpy as np

# Configure logging FIRST (before any logger usage)
logger = logging.getLogger(__name__)

# Fix MeCab config path for Apple Silicon Macs (must be set before importing fugashi/kokoro)
# MeCab/fugashi looks for /usr/local/etc/mecabrc but Homebrew installs to /opt/homebrew/etc/mecabrc
if platform.system() == "Darwin":
    mecab_config_paths = [
        "/opt/homebrew/etc/mecabrc",  # Apple Silicon Homebrew
        "/usr/local/etc/mecabrc",     # Intel Homebrew (or symlink)
    ]
    for mecab_path in mecab_config_paths:
        if os.path.exists(mecab_path):
            # Set both environment variables that fugashi/MeCab might check
            if "MECAB_DEFAULT_RC" not in os.environ:
                os.environ["MECAB_DEFAULT_RC"] = mecab_path
            if "MECABRC" not in os.environ:
                os.environ["MECABRC"] = mecab_path
            logger.debug(f"Set MeCab config path: {mecab_path}")
            break
    else:
        # If no mecabrc found, warn but continue (will fail when Kokoro tries to use it)
        logger.warning("MeCab config file not found. Kokoro TTS may not work. Run: scripts/setup_mecab.sh")

# Try to import Kokoro TTS (optional)
try:
    import fugashi
    
    # Store original Tagger class before patching (prevents recursion)
    _OriginalTagger = fugashi.Tagger
    
    # FIX: Create compatibility wrapper for GenericTagger
    # GenericTagger returns Node objects where node.feature is a tuple (ipadic format),
    # but cutlet/misaki expects node.feature.pron and node.feature.kana attributes.
    # Based on ipadic format: (pos, pos_sub1, pos_sub2, pos_sub3, pos_sub4, pos_sub5, base_form, reading, pronunciation)
    class FeatureAdapter:
        """Adapter that converts GenericTagger feature tuples to objects with .pron and .kana attributes."""
        def __init__(self, feature_tuple):
            """
            Args:
                feature_tuple: Tuple from GenericTagger in ipadic format
                    Format: (pos, pos_sub1, pos_sub2, pos_sub3, pos_sub4, pos_sub5, base_form, reading, pronunciation)
            """
            self._tuple = feature_tuple if isinstance(feature_tuple, tuple) else tuple()
            # Index 7 = reading (kana), Index 8 = pronunciation (pron) if available
            # For ipadic: indices are 0-8, reading is at 7, pronunciation at 8
            self.pron = self._tuple[8] if len(self._tuple) > 8 else (self._tuple[7] if len(self._tuple) > 7 else '')
            self.kana = self._tuple[7] if len(self._tuple) > 7 else ''
    
    class NodeAdapter:
        """
        Adapter that wraps GenericTagger Node to provide cutlet/misaki-compatible interface.
        
        Delegates all attributes to the original node, but converts feature tuple to object.
        """
        def __init__(self, node):
            self._node = node
            self.surface = node.surface
            # Convert feature tuple to FeatureAdapter object
            self.feature = FeatureAdapter(node.feature) if isinstance(node.feature, tuple) else node.feature
        
        def __getattr__(self, name):
            """Delegate all other attributes to the original node."""
            return getattr(self._node, name)
    
    class CompatibleTagger:
        """
        Compatibility wrapper for fugashi.Tagger that automatically falls back to GenericTagger
        and adapts its output format for cutlet/misaki compatibility.
        
        Based on fugashi documentation and Kokoro TTS requirements.
        """
        def __init__(self, *args, **kwargs):
            try:
                # Try original Tagger first (preferred) - use stored reference to avoid recursion
                self._tagger = _OriginalTagger(*args, **kwargs)
                self._use_generic = False
                logger.debug("Using standard fugashi.Tagger")
            except RuntimeError as e:
                if 'GenericTagger' in str(e) or 'Unknown dictionary format' in str(e):
                    # Fall back to GenericTagger with compatibility layer
                    logger.info("MeCab dictionary format incompatible, using GenericTagger with adapter")
                    self._tagger = fugashi.GenericTagger(*args, **kwargs)
                    self._use_generic = True
                else:
                    raise
        
        def __call__(self, text):
            """
            Tag text and return nodes compatible with cutlet/misaki.
            
            Args:
                text: Input text to tag
                
            Returns:
                List of Node objects compatible with cutlet expectations
            """
            result = self._tagger(text)
            
            if self._use_generic:
                # Wrap GenericTagger nodes with adapters
                return [NodeAdapter(node) for node in result]
            
            return result
    
    # Replace Tagger class with compatibility wrapper
    fugashi.Tagger = CompatibleTagger
    logger.debug("Applied fugashi.Tagger compatibility wrapper for Kokoro TTS")
    
    # Now import Kokoro (it will use the compatible Tagger)
    from kokoro import KPipeline
    KOKORO_AVAILABLE = True
except ImportError:
    KPipeline = None
    fugashi = None
    KOKORO_AVAILABLE = False


class TTSManager:
    """
    Manages text-to-speech generation using macOS native 'say' command.

    This class provides a clean interface for TTS functionality using
    the built-in macOS text-to-speech system. Fast and reliable on
    Apple Silicon Macs.

    Attributes:
        is_loaded: Whether TTS is available
        cache_dir: Directory for caching generated audio
    """

    def __init__(
        self,
        enable_cache: bool = True,
        cache_dir: str = "./yukio_data/tts_cache",
        speech_rate: int = 140,
        engine: Literal["native", "kokoro"] = None,
        voice: str = None
    ):
        """
        Initialize the TTS manager.

        Args:
            enable_cache: Whether to cache generated audio
            cache_dir: Directory for audio cache
            speech_rate: Speech rate in words per minute (default: 140, range: 50-400)
                        Lower = slower, clearer speech (recommended: 120-150)
                        Higher = faster speech
            engine: TTS engine to use ("native" for macOS say, "kokoro" for anime-style)
                   If None, auto-selects based on availability
            voice: Voice to use (for Kokoro: "af_bella" recommended, "af_sarah", "af_sky", etc.)
                  See Kokoro docs for full list. For native macOS, uses "Kyoko" or "Otoya"
        """
        self.enable_cache = enable_cache
        self.cache_dir = Path(cache_dir)
        # Default to slower rate for clearer, more natural speech
        self.speech_rate = max(50, min(400, speech_rate))  # Clamp between 50-400 WPM
        self.is_loaded = False
        self.engine = engine
        self.voice = voice
        self.kokoro_pipeline = None

        # Auto-select engine if not specified
        if self.engine is None:
            # Prefer Kokoro if available (anime-style voice)
            if KOKORO_AVAILABLE:
                self.engine = "kokoro"
                logger.info("🎌 Auto-selected Kokoro TTS for anime-style voice")
            elif platform.system() == "Darwin":
                self.engine = "native"
                logger.info("🍎 Auto-selected macOS native TTS")
            else:
                logger.warning("No TTS engine available")
                self.is_loaded = False
                return

        # Initialize selected engine
        if self.engine == "kokoro":
            self._init_kokoro()
        elif self.engine == "native":
            self._init_native()
        else:
            logger.error(f"Unknown TTS engine: {self.engine}")
            self.is_loaded = False
            return

        # Create cache directory if caching is enabled
        if self.enable_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache_index()

    def _init_kokoro(self):
        """Initialize Kokoro TTS engine."""
        if not KOKORO_AVAILABLE:
            logger.warning("Kokoro TTS not available. Install with: pip install kokoro")
            # Fallback to native if on macOS
            if platform.system() == "Darwin":
                logger.info("Falling back to macOS native TTS")
                self.engine = "native"
                self._init_native()
                return
            self.is_loaded = False
            return

        try:
            # Kokoro supports Japanese with lang_code="j" (Japanese)
            # Available voices for Japanese:
            # - af_heart: Cute, high-pitched (too squeaky)
            # - af_bella: Softer, gentler, more natural ⭐ Recommended
            # - af_sarah: Clear, professional
            # - af_sky: Neutral tone
            # - af_sam: Male voice
            lang_code = "j"  # Japanese
            # Use af_bella for a more natural, less squeaky voice
            default_voice = self.voice or "af_bella"  # Softer, more natural voice
            
            # Initialize GenericTagger first to ensure MeCab is properly configured
            # This fixes "Unknown dictionary format" errors
            try:
                import fugashi
                # Create GenericTagger to initialize MeCab with proper dictionary
                generic_tagger = fugashi.GenericTagger()
                logger.debug("GenericTagger initialized for Kokoro")
            except Exception as tagger_error:
                logger.warning(f"GenericTagger initialization warning: {tagger_error}")
                # Continue anyway - Kokoro might still work
            
            # Now initialize Kokoro pipeline
            try:
                self.kokoro_pipeline = KPipeline(lang_code=lang_code)
            except Exception as kokoro_error:
                # If still fails, try with explicit tagger parameter if supported
                if "Unknown dictionary format" in str(kokoro_error) or "GenericTagger" in str(kokoro_error):
                    logger.warning(f"Kokoro initialization issue: {kokoro_error}")
                    logger.info("Attempting alternative initialization...")
                    # Some versions of Kokoro might need different initialization
                    try:
                        # Try without lang_code first, then set it
                        self.kokoro_pipeline = KPipeline()
                        logger.info("✅ Kokoro initialized (alternative method)")
                    except Exception as alt_error:
                        logger.error(f"Alternative initialization also failed: {alt_error}")
                        raise kokoro_error
                else:
                    raise
            
            self.voice = default_voice
            self.is_loaded = True
            logger.info(f"🎌 Kokoro TTS initialized (voice: {self.voice}, lang: {lang_code})")
        except Exception as e:
            logger.error(f"Failed to initialize Kokoro TTS: {e}")
            # Fallback to native if on macOS
            if platform.system() == "Darwin":
                logger.info("Falling back to macOS native TTS")
                self.engine = "native"
                self._init_native()
            else:
                self.is_loaded = False

    def _init_native(self):
        """Initialize macOS native TTS engine."""
        if platform.system() != "Darwin":
            logger.warning("Native TTS only available on macOS")
            self.is_loaded = False
            return

        self.is_loaded = True
        logger.info(f"🍎 Using macOS native TTS (rate: {self.speech_rate} WPM)")

    def is_available(self) -> bool:
        """
        Check if TTS is available.

        Returns:
            True if TTS is available (macOS only), False otherwise
        """
        return self.is_loaded

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

    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key for the given text.

        Args:
            text: Input text

        Returns:
            MD5 hash of the text
        """
        return hashlib.md5(text.encode()).hexdigest()

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

    def _speak_kokoro(self, text: str) -> Optional[np.ndarray]:
        """
        Use Kokoro TTS for anime-style voice generation.
        
        Args:
            text: Text to convert to speech (Japanese or English)
            
        Returns:
            Audio array (numpy) or None if generation failed
        """
        if not self.kokoro_pipeline:
            return None
        
        try:
            # Kokoro pipeline is callable and returns an iterator
            # Format: (grapheme, phoneme, audio) tuples
            # Voice-specific speed overrides
            if self.voice == "af_bella":
                # af_bella uses direct speed setting (1.1 = slightly faster, more natural)
                speed = 1.05
            else:
                # Convert WPM to speed for other voices (160 WPM = 0.8x speed)
                speed = max(0.5, min(2.0, self.speech_rate / 200.0))
            
            audio_chunks = []
            for _gs, _ps, audio in self.kokoro_pipeline(
                text,
                voice=self.voice,
                speed=speed,
                split_pattern=r"\n+"
            ):
                # Collect audio chunks
                if isinstance(audio, np.ndarray):
                    audio_chunks.append(audio.astype(np.float32))
                else:
                    audio_chunks.append(np.array(audio, dtype=np.float32))
            
            # Concatenate all chunks
            if audio_chunks:
                full_audio = np.concatenate(audio_chunks)
                logger.debug(f"Generated Kokoro audio: {len(full_audio)} samples")
                return full_audio
            else:
                logger.warning("Kokoro generated no audio chunks")
                return None
            
        except Exception as e:
            logger.error(f"Kokoro TTS generation failed: {e}", exc_info=True)
            return None

    def _speak_native(self, text: str, output_path: Optional[str] = None, speech_rate: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Use macOS 'say' command for TTS.
        
        Uses the Japanese voice 'Kyoko' if available, otherwise default voice.
        
        Args:
            text: Text to convert to speech
            output_path: Optional path to save audio file
            speech_rate: Optional speech rate override (words per minute)
            
        Returns:
            Audio array (numpy) or None if generation failed
        """
        if platform.system() != "Darwin":
            logger.warning("Native TTS only available on macOS")
            return None
        
        try:
            # Use temporary file if no output path provided
            if output_path is None:
                output_path = tempfile.mktemp(suffix=".aiff")
            
            # Use provided rate or default
            rate = speech_rate if speech_rate is not None else self.speech_rate
            rate = max(50, min(400, rate))  # Clamp between 50-400 WPM
            
            # Try Japanese voice first, fallback to default
            voices = ["Kyoko", "Otoya"]  # Japanese voices on macOS
            voice_used = None
            
            for voice in voices:
                try:
                    # macOS say command: say -v VOICE -r RATE -o OUTPUT_FILE "TEXT"
                    # -r sets speech rate in words per minute (default ~200, we use slower for clarity)
                    subprocess.run(
                        ["say", "-v", voice, "-r", str(rate), "-o", output_path, text],
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                    voice_used = voice
                    break
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                    logger.debug(f"Voice {voice} not available: {e}")
                    continue
            
            if voice_used is None:
                # Fallback to default voice with rate control
                subprocess.run(
                    ["say", "-r", str(rate), "-o", output_path, text],
                    check=True,
                    capture_output=True,
                    timeout=30
                )
                voice_used = "default"
            
            logger.debug(f"Generated speech using macOS native TTS (voice: {voice_used})")
            
            # Load audio file and convert to numpy array
            try:
                import soundfile as sf
                audio, sample_rate = sf.read(output_path)
                # Ensure audio is in the correct format (mono, float32)
                if len(audio.shape) > 1:
                    audio = audio[:, 0]  # Take first channel if stereo
                return audio.astype(np.float32)
            except ImportError:
                logger.warning("soundfile not available - install with: pip install soundfile")
                return None
            except Exception as e:
                logger.error(f"Failed to load native TTS audio: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Native TTS generation failed: {e}")
            return None

    def generate_speech(
        self,
        text: str,
        use_cache: bool = True,
        verbose: bool = False,
        speech_rate: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Generate speech from text using macOS native TTS.

        Args:
            text: Input text to convert to speech
            use_cache: Whether to use cached audio if available
            verbose: Print generation progress
            speech_rate: Optional speech rate override (words per minute, 50-400)

        Returns:
            Audio array (numpy) or None if generation failed
        """
        if not self.is_available():
            logger.warning("TTS not available - macOS required")
            return None
        
        # Use provided rate or default
        rate = speech_rate if speech_rate is not None else self.speech_rate
        
        # Check cache first (but only if using default rate)
        if use_cache and speech_rate is None:
            cache_key = self._get_cache_key(text)
            cached_audio = self._get_cached_audio(cache_key)
            if cached_audio is not None:
                return cached_audio

        try:
            if verbose:
                logger.info(f"Generating speech for: {text[:50]}... (engine: {self.engine}, rate: {rate} WPM)")

            # Generate audio using selected engine
            if self.engine == "kokoro":
                audio = self._speak_kokoro(text)
            elif self.engine == "native":
                audio = self._speak_native(text, speech_rate=rate)
            else:
                logger.error(f"Unknown engine: {self.engine}")
                return None

            # Cache the result (only if using default rate)
            if use_cache and audio is not None and speech_rate is None:
                cache_key = self._get_cache_key(text)
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

            # Use soundfile to save
            import soundfile as sf
            sf.write(path, audio, sample_rate)

            logger.info(f"Saved audio to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            return False

    def generate_and_play(
        self,
        text: str,
        output_path: str = "./yukio_data/audio/tts_output.wav",
        auto_play: bool = True,
        speech_rate: Optional[int] = None
    ) -> bool:
        """
        Generate speech from text, save to file, and optionally play it.

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file (default: tts_output.wav)
            auto_play: Whether to automatically play the audio after generation
            speech_rate: Optional speech rate override (words per minute, 50-400)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("TTS not available")
            return False

        try:
            # Generate audio
            audio = self.generate_speech(text, speech_rate=speech_rate, verbose=True)
            if audio is None:
                logger.error("Failed to generate audio")
                return False

            # Determine sample rate based on engine
            sample_rate = 24000 if self.engine == "kokoro" else 44100

            # Save to file
            if not self.save_audio(output_path, audio, sample_rate=sample_rate):
                logger.error("Failed to save audio file")
                return False

            # Play audio if requested
            if auto_play:
                return self._play_audio(output_path)

            return True

        except Exception as e:
            logger.error(f"Failed to generate and play audio: {e}")
            return False

    def _play_audio(self, file_path: str) -> bool:
        """
        Play audio file using pygame.

        Args:
            file_path: Path to audio file

        Returns:
            True if successful, False otherwise
        """
        try:
            import pygame

            # Initialize pygame mixer
            pygame.mixer.init()

            # Load and play audio
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            # Wait for playback to finish
            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                clock.tick(10)

            # Clean up
            pygame.mixer.quit()

            logger.info(f"Played audio: {file_path}")
            return True

        except ImportError:
            logger.warning("pygame not available for audio playback. Install with: pip install pygame")
            # Fallback to system command (macOS)
            if platform.system() == "Darwin":
                try:
                    subprocess.run(["afplay", file_path], check=True, timeout=60)
                    logger.info(f"Played audio using afplay: {file_path}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to play audio with afplay: {e}")
                    return False
            return False
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            return False

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

    def __repr__(self) -> str:
        """String representation of TTSManager."""
        status = "available" if self.is_available() else "unavailable"
        return f"TTSManager(status={status}, platform={platform.system()})"


# Convenience functions for quick usage

def create_tts_manager(
    enable_tts: bool = True
) -> TTSManager:
    """
    Create a TTS manager instance with sensible defaults.

    Args:
        enable_tts: Whether to enable TTS (from config/env)

    Returns:
        TTSManager instance
    """
    if not enable_tts:
        logger.info("TTS disabled by configuration")

    return TTSManager()


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
        # Determine sample rate based on engine
        sample_rate = 24000 if tts_manager.engine == "kokoro" else 44100
        return tts_manager.save_audio(output_path, audio, sample_rate=sample_rate)

    return False


def generate_and_play(
    text: str,
    output_path: str = "./yukio_data/audio/tts_output.wav",
    tts_manager: Optional[TTSManager] = None,
    auto_play: bool = True,
    **kwargs
) -> bool:
    """
    Generate speech, save to file, and optionally play it.

    Args:
        text: Text to convert to speech
        output_path: Path to save audio file (default: tts_output.wav)
        tts_manager: Existing TTS manager (creates one if None)
        auto_play: Whether to automatically play the audio after generation
        **kwargs: Additional arguments for generate_speech()

    Returns:
        True if successful, False otherwise
    """
    if tts_manager is None:
        tts_manager = TTSManager()

    if not tts_manager.is_available():
        logger.warning("TTS not available")
        return False

    return tts_manager.generate_and_play(
        text=text,
        output_path=output_path,
        auto_play=auto_play,
        **kwargs
    )
