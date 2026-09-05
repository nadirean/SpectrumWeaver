"""Tests for the SpectrumAnalyzer class."""

import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.analyzers.audio_io import AudioInfo
from src.analyzers.spectrum_analyzer import SpectrumAnalyzer


@pytest.fixture
def mock_audio_file() -> Generator[str, None, None]:
    """Fixture to create a temporary audio file path."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        yield tmp_file.name
    # Cleanup
    Path(tmp_file.name).unlink(missing_ok=True)


@pytest.fixture
def mock_callback():
    """Fixture to create a mock callback function."""
    return Mock()


@pytest.fixture
def mock_audio_info():
    """Fixture to mock get_audio_info (10 s of audio at 44100 Hz)."""
    with patch('src.analyzers.spectrum_analyzer.get_audio_info') as mock:
        mock.return_value = AudioInfo(sample_rate=44100, duration=10.0, channels=2)
        yield mock


@pytest.fixture
def mock_empty_stream():
    """Fixture to mock iter_mono_chunks with no data (reader finishes immediately)."""
    with patch('src.analyzers.spectrum_analyzer.iter_mono_chunks') as mock:
        mock.return_value = iter(())
        yield mock


class TestSpectrumAnalyzer:
    """Test cases for the SpectrumAnalyzer class."""

    def test_spectrum_analyzer_init(self, mock_audio_file: str, mock_callback: Mock) -> None:
        """Test the initialization of the SpectrumAnalyzer."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)

        assert analyzer is not None
        assert analyzer.path == mock_audio_file
        assert analyzer.callback == mock_callback
        assert analyzer.fft_size == 2048  # default
        assert analyzer.hop_length == 512  # default (fft_size // 4)
        assert analyzer.batch_size == 16  # default
        assert analyzer.sample_rate is None  # not loaded yet
        assert not analyzer.is_running

    def test_spectrum_analyzer_init_with_custom_params(self, mock_audio_file: str, mock_callback: Mock) -> None:
        """Test initialization with custom parameters."""
        analyzer = SpectrumAnalyzer(
            path=mock_audio_file,
            callback=mock_callback,
            fft_size=4096,
            hop_length=1024,
            batch_size=32
        )

        assert analyzer.fft_size == 4096
        assert analyzer.hop_length == 1024
        assert analyzer.batch_size == 32

    def test_start_method(self, mock_audio_file: str, mock_callback: Mock,
                          mock_audio_info: Mock, mock_empty_stream: Mock) -> None:
        """Test the start method loads metadata correctly."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)

        metadata = analyzer.start()
        analyzer.stop()

        # Verify metadata structure
        assert 'sample_rate' in metadata
        assert 'duration' in metadata
        assert 'total_samples' in metadata
        assert 'fft_size' in metadata
        assert 'hop_length' in metadata
        assert 'frequencies' in metadata
        assert 'num_time_frames' in metadata

        # Verify values
        assert metadata['sample_rate'] == 44100
        assert metadata['duration'] == 10.0
        assert metadata['fft_size'] == 2048
        assert metadata['hop_length'] == 512

        # Verify audio info call
        mock_audio_info.assert_called_once_with(mock_audio_file)

        # In linear mode (default), frequencies should have 1025 bins from 0 to 22050 Hz
        assert len(metadata['frequencies']) == 1025
        assert metadata['frequencies'][0] == 0.0
        assert metadata['frequencies'][-1] == 22050.0

    def test_start_method_192khz(self, mock_audio_file: str, mock_callback: Mock,
                                mock_empty_stream: Mock) -> None:
        """Test the start method with 192 kHz audio."""
        with patch('src.analyzers.spectrum_analyzer.get_audio_info') as mock_info:
            mock_info.return_value = AudioInfo(sample_rate=192000, duration=10.0, channels=2)
            analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)
            metadata = analyzer.start()
            analyzer.stop()

            assert metadata['sample_rate'] == 192000
            assert len(metadata['frequencies']) == 1025
            assert metadata['frequencies'][0] == 0.0
            assert metadata['frequencies'][-1] == 96000.0


    def test_fft_output_reaches_callback(self, mock_audio_file: str, mock_callback: Mock,
                                         mock_audio_info: Mock) -> None:
        """Test that decoded chunks are framed, FFT'd, and delivered to the callback."""
        chunks = [
            np.full(4096, 0.5, dtype=np.float32),
            np.full(4096, 0.25, dtype=np.float32),
        ]
        with patch('src.analyzers.spectrum_analyzer.iter_mono_chunks', return_value=iter(chunks)):
            analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)
            analyzer.start()

            # Wait for the end-of-processing signal
            deadline = time.time() + 5.0
            while not analyzer.is_finished and time.time() < deadline:
                time.sleep(0.01)
            analyzer.stop()

        assert analyzer.is_finished
        # Frames delivered: callback called with batch(es) and the -1 end signal
        calls = mock_callback.call_args_list
        assert calls, "callback was never called"
        last_call = calls[-1].args
        assert last_call[0] == -1  # end signal

    def test_stop_method(self, mock_audio_file: str, mock_callback: Mock) -> None:
        """Test the stop method."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)

        # Should not raise error even if not running
        analyzer.stop()

        # Simulate running state
        analyzer.is_running = True
        analyzer.stop()

        assert not analyzer.is_running

    def test_already_running_error(self, mock_audio_file: str, mock_callback: Mock,
                                   mock_audio_info: Mock, mock_empty_stream: Mock) -> None:
        """Test that starting an already running analyzer raises error."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)

        analyzer.start()

        # Try to start again - should raise error
        with pytest.raises(RuntimeError, match="Analyzer is already running"):
            analyzer.start()

        analyzer.stop()

    def test_metadata_loading_failure(self, mock_audio_file: str, mock_callback: Mock) -> None:
        """Test handling of metadata loading failure."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)

        # Mock failure
        with patch('src.analyzers.spectrum_analyzer.get_audio_info',
                   side_effect=Exception("Failed to load")):
            with pytest.raises(RuntimeError, match="Failed to load audio metadata"):
                analyzer.start()

    def test_properties_before_start(self, mock_audio_file: str, mock_callback: Mock) -> None:
        """Test analyzer properties before calling start."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback)

        assert analyzer.sample_rate is None
        assert analyzer.duration is None
        assert analyzer.total_samples is None
        assert not analyzer.is_running
        assert not analyzer.is_finished

    def test_hop_length_default_calculation(self, mock_audio_file: str, mock_callback: Mock) -> None:
        """Test that hop_length defaults to fft_size // 4."""
        analyzer = SpectrumAnalyzer(mock_audio_file, mock_callback, fft_size=8192)

        assert analyzer.hop_length == 2048  # 8192 // 4

    def test_different_file_paths(self, mock_callback: Mock) -> None:
        """Test initialization with different file paths."""
        test_paths = [
            "test.wav",
            "path/to/audio.mp3",
            "C:\\Users\\test\\audio.flac",
            "/usr/local/audio.ogg",
            "",  # Empty path
        ]

        for path in test_paths:
            analyzer = SpectrumAnalyzer(path, mock_callback)
            assert analyzer.path == path
