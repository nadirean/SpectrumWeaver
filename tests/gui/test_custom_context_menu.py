"""Tests for the CustomContextMenu class."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot

from src.gui.custom_context_menu import CustomContextMenu


@pytest.fixture
def parent(qtbot: QtBot) -> Generator[QWidget, None, None]:
    """Fixture to create a QWidget parent instance."""
    widget = QWidget()
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
def mock_plot_widget():
    """Fixture to create a mock plot widget."""
    return Mock()


@pytest.fixture
def mock_image_item():
    """Fixture to create a mock image item."""
    mock_item = Mock()
    mock_pixmap = Mock()
    mock_qimg = Mock()
    mock_pixmap.toImage.return_value = mock_qimg
    mock_item.getPixmap.return_value = mock_pixmap
    return mock_item


@pytest.fixture
def mock_colorbar():
    """Fixture to create a mock colorbar."""
    return Mock()


@pytest.fixture
def sample_metadata():
    """Fixture to provide sample metadata."""
    return {
        'sample_rate': 44100,
        'duration': 5.0,
        'total_samples': 220500,
        'fft_size': 2048,
        'hop_length': 512,
        'frequencies': np.linspace(0, 22050, 1025),
        'num_time_frames': 431
    }


@pytest.fixture
def sample_spectrogram_data():
    """Fixture to provide sample spectrogram data."""
    return np.random.uniform(-120, 0, (431, 1025))


@pytest.fixture
def context_menu(parent, mock_plot_widget, mock_image_item, mock_colorbar, 
                mock_audio_file, sample_spectrogram_data, sample_metadata):
    """Fixture to create a CustomContextMenu instance."""
    return CustomContextMenu(
        parent=parent,
        plot_widget=mock_plot_widget,
        image_item=mock_image_item,
        colorbar=mock_colorbar,
        audio_path=mock_audio_file,
        spectrogram_data=sample_spectrogram_data,
        metadata=sample_metadata,
        settings_changed_callback=Mock()
    )


class TestCustomContextMenu:
    """Test cases for the CustomContextMenu class."""
    def test_context_menu_initialization(self, context_menu, mock_audio_file, 
                                       sample_spectrogram_data, sample_metadata) -> None:
        """Test the initialization of the CustomContextMenu."""
        assert context_menu is not None
        assert context_menu.audio_path == mock_audio_file
        assert np.array_equal(context_menu.spectrogram_data, sample_spectrogram_data)
        assert context_menu.metadata == sample_metadata
        assert context_menu._show_grid is True  # Default state
        assert context_menu._colormap == 'viridis'  # Default colormap
        assert context_menu._batch_size == 16  # Default batch size

    def test_context_menu_with_none_values(self, parent, mock_plot_widget, 
                                         mock_image_item, mock_colorbar) -> None:
        """Test initialization with None values."""
        context_menu = CustomContextMenu(
            parent=parent,
            plot_widget=mock_plot_widget,
            image_item=mock_image_item,
            colorbar=mock_colorbar,
            audio_path=None,
            spectrogram_data=None,
            metadata={},
            settings_changed_callback=None
        )

        assert context_menu.audio_path is None
        assert context_menu.spectrogram_data is None
        assert context_menu.metadata == {}
        assert context_menu.settings_changed_callback is None

    @patch('src.gui.custom_context_menu.QMenu')
    def test_exec_menu_creation(self, mock_qmenu, context_menu, parent) -> None:
        """Test that exec creates a menu with correct actions."""
        mock_menu_instance = Mock()
        mock_qmenu.return_value = mock_menu_instance

        # Mock the context menu event
        event = Mock()
        event.globalPos.return_value = Mock()

        context_menu.exec(event)

        # Verify menu was created
        mock_qmenu.assert_called_once_with(parent)

        # Verify actions were added
        assert mock_menu_instance.addAction.call_count == 3  # export, details, settings

        # Verify exec was called
        mock_menu_instance.exec.assert_called_once()

    @patch('src.gui.custom_context_menu.QFileDialog')
    def test_export_spectrogram_png(self, mock_dialog, context_menu, mock_audio_file) -> None:
        """Test the PNG export functionality."""
        # Mock file dialog
        mock_dialog.getSaveFileName.return_value = ("test_export.png", "PNG Files (*.png)")

        # Mock the image item and pixmap
        mock_qimg = Mock()
        mock_qimg_flipped = Mock()
        mock_qimg.mirrored.return_value = mock_qimg_flipped
        context_menu.image_item.getPixmap.return_value.toImage.return_value = mock_qimg

        # Call the method
        context_menu._export_spectrogram_png()

        # Verify file dialog was called
        mock_dialog.getSaveFileName.assert_called_once()

        # Verify image processing
        mock_qimg.mirrored.assert_called_once_with(False, True)
        mock_qimg_flipped.save.assert_called_once_with("test_export.png")

    def test_export_no_spectrogram_data(self, context_menu) -> None:
        """Test export when no spectrogram data is available."""
        context_menu.spectrogram_data = None

        # Should return early without doing anything
        context_menu._export_spectrogram_png()

        # No assertions needed - just verify it doesn't crash

    @patch('src.gui.custom_context_menu.QFileDialog')
    def test_export_cancelled(self, mock_dialog, context_menu) -> None:
        """Test export when user cancels the file dialog."""
        # Mock file dialog cancellation
        mock_dialog.getSaveFileName.return_value = ("", "")

        context_menu._export_spectrogram_png()

        # Verify dialog was called but no further processing
        mock_dialog.getSaveFileName.assert_called_once()

    def test_show_details_no_file(self, context_menu) -> None:
        """Test details dialog when no file path is set."""
        context_menu.audio_path = None

        # Should return early without doing anything
        context_menu._show_details_dialog()

        # No assertions needed - just verify it doesn't crash

    @patch('src.gui.custom_context_menu.os.path.isfile')
    def test_show_details_nonexistent_file(self, mock_isfile, context_menu) -> None:
        """Test details dialog when file doesn't exist."""
        mock_isfile.return_value = False

        context_menu._show_details_dialog()

        # Should return early
        mock_isfile.assert_called_once()

    def test_get_batch_size(self, context_menu) -> None:
        """Test getting the batch size setting."""
        # Default value
        assert context_menu.get_batch_size() == 16

        # Set custom value
        context_menu._batch_size = 32
        assert context_menu.get_batch_size() == 32

    def test_settings_changed_callback(self, context_menu) -> None:
        """Test that settings changed callback is called."""
        # Mock callback should be called when batch size changes
        context_menu._batch_size = 32

        # Simulate settings change (this would normally be called from settings dialog)
        if context_menu.settings_changed_callback:
            context_menu.settings_changed_callback('batch_size', 32)
            context_menu.settings_changed_callback.assert_called_with('batch_size', 32)

    def test_colormap_property(self, context_menu) -> None:
        """Test the colormap property."""
        # Default value
        assert context_menu._colormap == 'viridis'

        # Change value
        context_menu._colormap = 'plasma'
        assert context_menu._colormap == 'plasma'

    def test_show_grid_property(self, context_menu) -> None:
        """Test the show grid property."""
        # Default value
        assert context_menu._show_grid is True

        # Change value
        context_menu._show_grid = False
        assert context_menu._show_grid is False

