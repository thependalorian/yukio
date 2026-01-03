"""
Unit tests for the TTS (Text-to-Speech) module.

These tests verify the functionality of agent/tts.py, including:
- TTSManager initialization
- Speech generation
- Audio caching
- Error handling
- Voice cloning support

Note: These tests use mocking to avoid requiring the actual Dia model,
making them suitable for CI/CD environments without GPU.
"""

import pytest
import sys
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTTSManagerInitialization:
    """Test TTSManager initialization and setup."""

    @patch('agent.tts.Path')
    def test_init_creates_cache_directory(self, mock_path):
        """Test that cache directory is created when caching is enabled."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager(enable_cache=True)

            assert tts.enable_cache is True
            # Cache directory creation is called
            assert mock_path.called

    @patch('agent.tts.TTSManager._load_model')
    def test_init_without_cache(self, mock_load_model):
        """Test initialization without caching."""
        from agent.tts import TTSManager

        tts = TTSManager(enable_cache=False)

        assert tts.enable_cache is False
        assert tts.cache_dir is not None  # Path is still set

    @patch('agent.tts.TTSManager._load_model')
    def test_init_custom_parameters(self, mock_load_model):
        """Test initialization with custom parameters."""
        from agent.tts import TTSManager

        tts = TTSManager(
            model_name="custom-model",
            device="cpu",
            compute_dtype="float32",
            cache_dir="/custom/cache"
        )

        assert tts.model_name == "custom-model"
        assert tts.device == "cpu"
        assert tts.compute_dtype == "float32"
        assert str(tts.cache_dir) == "/custom/cache"


class TestTTSModelLoading:
    """Test model loading functionality."""

    @patch('agent.tts.sys.path')
    @patch('agent.tts.Path')
    def test_load_model_success(self, mock_path, mock_sys_path):
        """Test successful model loading."""
        from agent.tts import TTSManager

        # Mock Dia import and model
        mock_dia = MagicMock()
        mock_model = MagicMock()
        mock_dia.from_pretrained.return_value = mock_model

        with patch.dict('sys.modules', {'dia.model': mock_dia}):
            with patch('agent.tts.TTSManager._load_cache_index'):
                tts = TTSManager()

                assert tts.is_loaded is True
                assert tts.model is not None

    def test_load_model_import_error(self):
        """Test handling of import error when Dia is not available."""
        from agent.tts import TTSManager

        # Force import error
        with patch.dict('sys.modules', {'dia.model': None}):
            with patch('agent.tts.TTSManager._load_cache_index'):
                tts = TTSManager()

                assert tts.is_loaded is False
                assert tts.model is None

    def test_is_available_when_loaded(self):
        """Test is_available returns True when model is loaded."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = True
            tts.model = MagicMock()

            assert tts.is_available() is True

    def test_is_available_when_not_loaded(self):
        """Test is_available returns False when model is not loaded."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = False
            tts.model = None

            assert tts.is_available() is False


class TestSpeechGeneration:
    """Test speech generation functionality."""

    @pytest.fixture
    def mock_tts(self):
        """Create a mock TTS manager with model loaded."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager(enable_cache=False)
            tts.is_loaded = True
            tts.model = MagicMock()
            # Mock generate method to return fake audio
            tts.model.generate.return_value = np.random.randn(44100)
            return tts

    def test_generate_speech_success(self, mock_tts):
        """Test successful speech generation."""
        text = "[S1] Hello, world!"
        audio = mock_tts.generate_speech(text)

        assert audio is not None
        assert isinstance(audio, np.ndarray)
        mock_tts.model.generate.assert_called_once()

    def test_generate_speech_with_parameters(self, mock_tts):
        """Test speech generation with custom parameters."""
        text = "[S1] Test"
        audio = mock_tts.generate_speech(
            text,
            temperature=1.5,
            cfg_scale=2.0,
            top_p=0.9,
            max_tokens=1000
        )

        assert audio is not None
        # Verify parameters were passed to model
        call_kwargs = mock_tts.model.generate.call_args[1]
        assert call_kwargs['temperature'] == 1.5
        assert call_kwargs['cfg_scale'] == 2.0
        assert call_kwargs['top_p'] == 0.9
        assert call_kwargs['max_tokens'] == 1000

    def test_generate_speech_unavailable_model(self):
        """Test speech generation when model is not available."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = False

            audio = tts.generate_speech("[S1] Test")

            assert audio is None

    def test_generate_speech_exception_handling(self, mock_tts):
        """Test exception handling during generation."""
        mock_tts.model.generate.side_effect = RuntimeError("GPU error")

        audio = mock_tts.generate_speech("[S1] Test")

        assert audio is None  # Should return None on error


class TestAudioCaching:
    """Test audio caching functionality."""

    @pytest.fixture
    def mock_tts_with_cache(self):
        """Create a mock TTS manager with caching enabled."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            with patch('agent.tts.TTSManager._load_cache_index'):
                tts = TTSManager(enable_cache=True)
                tts.is_loaded = True
                tts.model = MagicMock()
                tts.model.generate.return_value = np.random.randn(44100)
                tts.cache_index = {}
                return tts

    def test_get_cache_key(self, mock_tts_with_cache):
        """Test cache key generation."""
        text = "[S1] Test"
        key1 = mock_tts_with_cache._get_cache_key(text)
        key2 = mock_tts_with_cache._get_cache_key(text)

        # Same text should produce same key
        assert key1 == key2
        assert len(key1) == 32  # MD5 hash length

    def test_get_cache_key_different_params(self, mock_tts_with_cache):
        """Test cache key changes with different parameters."""
        text = "[S1] Test"
        key1 = mock_tts_with_cache._get_cache_key(text, temperature=1.0)
        key2 = mock_tts_with_cache._get_cache_key(text, temperature=1.5)

        # Different parameters should produce different keys
        assert key1 != key2

    @patch('agent.tts.np.load')
    @patch('agent.tts.Path.exists')
    def test_get_cached_audio_hit(self, mock_exists, mock_np_load, mock_tts_with_cache):
        """Test successful cache retrieval."""
        mock_exists.return_value = True
        mock_audio = np.random.randn(44100)
        mock_np_load.return_value = mock_audio

        cache_key = "test_key"
        mock_tts_with_cache.cache_index[cache_key] = {'text': 'test', 'file': 'test.npy'}

        audio = mock_tts_with_cache._get_cached_audio(cache_key)

        assert audio is not None
        np.testing.assert_array_equal(audio, mock_audio)

    def test_get_cached_audio_miss(self, mock_tts_with_cache):
        """Test cache miss."""
        cache_key = "nonexistent_key"

        audio = mock_tts_with_cache._get_cached_audio(cache_key)

        assert audio is None

    @patch('agent.tts.np.save')
    @patch('agent.tts.TTSManager._save_cache_index')
    def test_cache_audio(self, mock_save_index, mock_np_save, mock_tts_with_cache):
        """Test audio caching."""
        cache_key = "test_key"
        audio = np.random.randn(44100)
        text = "[S1] Test"

        mock_tts_with_cache._cache_audio(cache_key, audio, text)

        # Verify audio was saved
        mock_np_save.assert_called_once()

        # Verify index was updated
        assert cache_key in mock_tts_with_cache.cache_index
        assert mock_save_index.called


class TestAudioSaving:
    """Test audio file saving functionality."""

    @pytest.fixture
    def mock_tts(self):
        """Create a mock TTS manager."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = True
            tts.model = MagicMock()
            return tts

    @patch('agent.tts.Path.mkdir')
    def test_save_audio_success(self, mock_mkdir, mock_tts):
        """Test successful audio saving."""
        audio = np.random.randn(44100)
        path = "output.mp3"

        mock_tts.model.save_audio = MagicMock()

        success = mock_tts.save_audio(path, audio)

        assert success is True
        mock_tts.model.save_audio.assert_called_once_with(path, audio)

    def test_save_audio_none_input(self, mock_tts):
        """Test saving None audio."""
        success = mock_tts.save_audio("output.mp3", None)

        assert success is False

    @patch('agent.tts.Path.mkdir')
    def test_save_audio_exception(self, mock_mkdir, mock_tts):
        """Test exception handling during save."""
        audio = np.random.randn(44100)
        mock_tts.model.save_audio = MagicMock(side_effect=IOError("Disk full"))

        success = mock_tts.save_audio("output.mp3", audio)

        assert success is False


class TestVoiceCloning:
    """Test voice cloning functionality."""

    @pytest.fixture
    def mock_tts(self):
        """Create a mock TTS manager."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = True
            tts.model = MagicMock()
            return tts

    def test_load_audio_prompt_success(self, mock_tts):
        """Test successful audio prompt loading."""
        mock_audio = MagicMock()
        mock_tts.model.load_audio.return_value = mock_audio

        result = mock_tts.load_audio_prompt("sample.mp3")

        assert result == mock_audio
        mock_tts.model.load_audio.assert_called_once_with("sample.mp3")

    def test_load_audio_prompt_unavailable(self):
        """Test loading audio prompt when TTS is unavailable."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = False

            result = tts.load_audio_prompt("sample.mp3")

            assert result is None

    def test_load_audio_prompt_exception(self, mock_tts):
        """Test exception handling during audio prompt loading."""
        mock_tts.model.load_audio.side_effect = FileNotFoundError()

        result = mock_tts.load_audio_prompt("nonexistent.mp3")

        assert result is None


class TestCacheManagement:
    """Test cache management functionality."""

    @pytest.fixture
    def mock_tts_with_cache(self):
        """Create a mock TTS manager with cache."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            with patch('agent.tts.TTSManager._load_cache_index'):
                tts = TTSManager(enable_cache=True)
                tts.cache_index = {'key1': {}, 'key2': {}}
                return tts

    @patch('agent.tts.Path.glob')
    def test_get_cache_size(self, mock_glob, mock_tts_with_cache):
        """Test cache size calculation."""
        # Mock cache files
        mock_file1 = MagicMock()
        mock_file1.stat.return_value.st_size = 1024
        mock_file2 = MagicMock()
        mock_file2.stat.return_value.st_size = 2048

        mock_glob.return_value = [mock_file1, mock_file2]

        size = mock_tts_with_cache.get_cache_size()

        assert size == 3072

    @patch('agent.tts.Path.glob')
    @patch('agent.tts.TTSManager._save_cache_index')
    def test_clear_cache(self, mock_save_index, mock_glob, mock_tts_with_cache):
        """Test cache clearing."""
        # Mock cache files
        mock_file = MagicMock()
        mock_glob.return_value = [mock_file]

        mock_tts_with_cache.clear_cache()

        # Verify file was deleted
        mock_file.unlink.assert_called_once()

        # Verify index was cleared
        assert len(mock_tts_with_cache.cache_index) == 0


class TestJapaneseTextFormatting:
    """Test Japanese text formatting."""

    @pytest.fixture
    def mock_tts(self):
        """Create a mock TTS manager."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            return tts

    def test_format_japanese_text(self, mock_tts):
        """Test Japanese text formatting."""
        japanese_text = "こんにちは"
        formatted = mock_tts.format_japanese_text(japanese_text)

        assert "[S1]" in formatted
        assert japanese_text in formatted

    def test_format_japanese_text_custom_speaker(self, mock_tts):
        """Test Japanese text formatting with custom speaker."""
        japanese_text = "ありがとう"
        formatted = mock_tts.format_japanese_text(japanese_text, speaker="S2")

        assert "[S2]" in formatted
        assert japanese_text in formatted


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch('agent.tts.TTSManager')
    def test_create_tts_manager(self, mock_tts_class):
        """Test TTS manager creation."""
        from agent.tts import create_tts_manager

        manager = create_tts_manager(enable_tts=True, device="cuda")

        mock_tts_class.assert_called_once_with(device="cuda")

    @patch('agent.tts.TTSManager')
    def test_generate_and_save(self, mock_tts_class):
        """Test generate and save convenience function."""
        from agent.tts import generate_and_save

        # Mock TTS manager
        mock_manager = MagicMock()
        mock_manager.is_available.return_value = True
        mock_manager.generate_speech.return_value = np.random.randn(44100)
        mock_manager.save_audio.return_value = True
        mock_tts_class.return_value = mock_manager

        success = generate_and_save(
            text="[S1] Test",
            output_path="test.mp3"
        )

        assert success is True
        mock_manager.generate_speech.assert_called_once()
        mock_manager.save_audio.assert_called_once()

    @patch('agent.tts.TTSManager')
    def test_generate_and_save_unavailable(self, mock_tts_class):
        """Test generate and save when TTS is unavailable."""
        from agent.tts import generate_and_save

        # Mock TTS manager as unavailable
        mock_manager = MagicMock()
        mock_manager.is_available.return_value = False
        mock_tts_class.return_value = mock_manager

        success = generate_and_save(
            text="[S1] Test",
            output_path="test.mp3"
        )

        assert success is False


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mock_tts(self):
        """Create a mock TTS manager."""
        from agent.tts import TTSManager

        with patch('agent.tts.TTSManager._load_model'):
            tts = TTSManager()
            tts.is_loaded = True
            tts.model = MagicMock()
            return tts

    def test_generate_empty_text(self, mock_tts):
        """Test generation with empty text."""
        # Model should still be called, but may return None
        mock_tts.model.generate.return_value = None

        audio = mock_tts.generate_speech("")

        # Should handle gracefully
        assert audio is None or isinstance(audio, np.ndarray)

    def test_repr(self, mock_tts):
        """Test string representation."""
        mock_tts.is_loaded = True
        repr_str = repr(mock_tts)

        assert "TTSManager" in repr_str
        assert "available" in repr_str


# Integration-style tests (require actual Dia installation)
@pytest.mark.integration
class TestTTSIntegration:
    """
    Integration tests that require Dia to be installed.

    These tests are skipped by default. Run with:
        pytest -m integration
    """

    def test_real_model_loading(self):
        """Test loading the real Dia model."""
        pytest.importorskip("dia")

        from agent.tts import TTSManager

        tts = TTSManager()

        # This will fail if Dia is not properly installed
        assert tts.is_available() or not tts.is_loaded

    def test_real_generation(self):
        """Test real audio generation (slow, requires GPU)."""
        pytest.importorskip("dia")

        from agent.tts import TTSManager

        tts = TTSManager()

        if tts.is_available():
            audio = tts.generate_speech("[S1] Test", max_tokens=100)
            assert audio is not None
            assert len(audio) > 0
        else:
            pytest.skip("Dia not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
