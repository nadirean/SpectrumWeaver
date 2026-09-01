"""Tests for the SpectrumViewer class."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

import pytest
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout
from pytestqt.qtbot import QtBot
import pyqtgraph as pg

from src.gui.spectrum_viewer import SpectrumViewer


@pytest.fixture
def parent(qtbot: QtBot) -> Generator[QStackedWidget, None, None]:
    """Fixture to create a QStackedWidget parent instance."""
    widget = QStackedWidget()
    yield widget

    # Cleanup
    try:
        widget.close()
        widget.deleteLater()
    except RuntimeError:
        # The widget is already closed
        pass


@pytest.fixture
def mock_audio_file() -> Generator[str, None, None]:
    """Fixture to create a temporary audio file path."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        yield tmp_file.name

    # Cleanup
    Path(tmp_file.name).unlink(missing_ok=True)


@pytest.fixture
def mock_spectrum_analyzer():
    """Fixture to create a mock SpectrumAnalyzer."""
    with patch('src.gui.spectrum_viewer.SpectrumAnalyzer') as mock:
        mock_instance = Mock()
        mock_instance.start.return_value = {
            'sample_rate': 44100,
            'duration': 5.0,
            'total_samples': 220500,
            'fft_size': 2048,
            'hop_length': 512,
            'frequencies': np.linspace(0, 22050, 1025),
            'num_time_frames': 431
        }
        mock_instance.is_running = False
        mock.return_value = mock_instance
        yield mock


class TestSpectrumViewer:
    """Test cases for the SpectrumViewer class."""

    def test_spectrum_viewer_init(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test the initialization of the SpectrumViewer."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        assert viewer is not None
        assert viewer.parent() is parent
        assert viewer.audio_path == mock_audio_file
        assert isinstance(viewer.plot_widget, pg.PlotWidget)
        assert isinstance(viewer.image_item, pg.ImageItem)
        assert viewer.analyzer is not None

    def test_spectrum_viewer_layout(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test the layout setup of the SpectrumViewer."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check layout is set
        assert isinstance(viewer.layout(), QVBoxLayout)

        # Plot lives in the inner content stack, not the top-level layout
        layout = viewer.layout()
        assert layout.indexOf(viewer._content_stack) != -1
        assert viewer._content_stack.indexOf(viewer.plot_widget) != -1
        assert viewer._content_stack.currentWidget() is viewer.plot_widget

    def test_spectrum_analyzer_creation(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that SpectrumAnalyzer is created with correct parameters."""
        SpectrumViewer(parent, mock_audio_file)

        # Verify SpectrumAnalyzer was called with correct parameters
        mock_spectrum_analyzer.assert_called_once()
        call_args = mock_spectrum_analyzer.call_args
        assert call_args[1]['path'] == mock_audio_file
        assert 'callback' in call_args[1]
        assert call_args[1]['fft_size'] == 2048
        assert call_args[1]['hop_length'] == 512
        assert call_args[1]['batch_size'] == 16

    def test_metadata_handling(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that metadata is properly handled."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check metadata was set
        assert viewer.metadata is not None
        assert 'sample_rate' in viewer.metadata
        assert 'duration' in viewer.metadata
        assert 'frequencies' in viewer.metadata

    def test_drag_and_drop_setup(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that drag and drop is properly set up."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check accepts drops
        assert viewer.acceptDrops()

    def test_context_menu_setup(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that context menu is properly set up."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check context menu is created
        assert viewer.context_menu is not None
        assert viewer.context_menu.audio_path == mock_audio_file

    def test_load_audio_method(self, parent: QStackedWidget, mock_spectrum_analyzer) -> None:
        """Test the load_audio method."""
        viewer = SpectrumViewer(parent)

        # Load a new audio file
        new_path = "new_audio.wav"
        viewer.load_audio(new_path)

        # Check audio path was updated
        assert viewer.audio_path == new_path

        # Check analyzer was recreated
        mock_spectrum_analyzer.assert_called()
        assert viewer._content_stack.currentWidget() is viewer.plot_widget

    def test_no_path_initialization(self, parent: QStackedWidget, mock_spectrum_analyzer) -> None:
        """Test initialization with no audio path."""
        viewer = SpectrumViewer(parent)

        assert viewer is not None
        assert viewer.audio_path is None
        assert viewer.analyzer is None
        assert viewer._content_stack.currentWidget() is viewer._empty_page
        assert viewer._empty_page.acceptDrops()
        labels = viewer._empty_page.findChildren(QLabel)
        texts = [label.text() for label in labels]
        assert "Drop an audio file here" in texts
        assert "WAV, FLAC, OGG, MP3, M4A, AAC" in texts

    def test_signals_connection(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that signals are properly connected."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check signals exist
        assert hasattr(viewer, 'frames_received')
        assert hasattr(viewer, 'analysis_complete')

    def test_spectrogram_data_initialization(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that spectrogram data is properly initialized."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check spectrogram data array is created
        assert viewer.spectrogram_data is not None
        assert isinstance(viewer.spectrogram_data, np.ndarray)
        assert viewer.spectrogram_data.shape == (431, 1025)  # Based on mock metadata

    def test_analysis_start_called(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that analysis is started when viewer is created with audio path."""
        SpectrumViewer(parent, mock_audio_file)

        # Verify start was called on analyzer
        mock_spectrum_analyzer.return_value.start.assert_called_once()

    def test_plot_title_setting(self, parent: QStackedWidget, mock_audio_file: str, mock_spectrum_analyzer) -> None:
        """Test that plot title is set correctly."""
        viewer = SpectrumViewer(parent, mock_audio_file)

        # Check title is set
        assert viewer.plot_widget.plotItem.titleLabel.text == mock_audio_file
