"""Tests for the SpectrumWeaver main application class."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QStackedWidget, QWidget
from pytestqt.qtbot import QtBot

from src.spectrum_weaver import SpectrumWeaver


@pytest.fixture
def mock_qss_file() -> Generator[str, None, None]:
    """Fixture to create a temporary QSS file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".qss", delete=False) as tmp_file:
        tmp_file.write("""
        /* Test QSS styles */
        QWidget {
            background-color: #2b2b2b;
            color: white;
        }
        """)
        yield tmp_file.name

    # Cleanup
    Path(tmp_file.name).unlink(missing_ok=True)


@pytest.fixture
def mock_audio_file() -> Generator[str, None, None]:
    """Fixture to create a temporary audio file path."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        yield tmp_file.name

    # Cleanup
    Path(tmp_file.name).unlink(missing_ok=True)


class TestSpectrumWeaver:
    """Test cases for the SpectrumWeaver main application class."""

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_spectrum_weaver_init(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test the initialization of the SpectrumWeaver application."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        assert app is not None
        assert isinstance(app.hBoxLayout, QHBoxLayout)
        assert isinstance(app.stacked_widget, QStackedWidget)
        assert isinstance(app.spectrum_viewer, QWidget)

        # Verify QSS file was read
        mock_read_text.assert_called_once_with(encoding="utf-8")

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_window_properties(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test the window properties and initialization."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        assert app.windowTitle() == "SpectrumWeaver"
        assert app.size() == QSize(960, 640)
        assert app.layout() is app.hBoxLayout

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_layout_setup(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test the layout setup and widget arrangement."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Check layout margins
        margins = app.hBoxLayout.contentsMargins()
        assert margins.left() == 16
        assert margins.top() == 48
        assert margins.right() == 16
        assert margins.bottom() == 16

        # Check that stacked widget is added to layout
        assert app.hBoxLayout.indexOf(app.stacked_widget) != -1

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_stacked_widget_initial_state(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test the initial state of the stacked widget."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Check that spectrum viewer is the initial widget
        assert app.stacked_widget.count() == 1
        assert app.stacked_widget.widget(0) is app.spectrum_viewer
        assert app.stacked_widget.currentWidget() is app.spectrum_viewer

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_window_icon_setup(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test that the window icon is properly set."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Check that window icon is set
        icon = app.windowIcon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_qss_loading(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test that QSS styles are loaded correctly."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        test_styles = """
        QWidget {
            background-color: #2b2b2b;
            color: white;
        }
        """
        mock_read_text.return_value = test_styles

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Verify file was opened and read
        mock_read_text.assert_called_once_with(encoding="utf-8")

        # Check that stylesheet was applied
        assert app.styleSheet() == test_styles

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_init_window_method(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test the _init_window method behavior."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Verify window properties set by _init_window
        assert app.windowTitle() == "SpectrumWeaver"
        assert app.size() == QSize(960, 640)
        assert app.layout() is app.hBoxLayout
        assert app.hBoxLayout.indexOf(app.stacked_widget) != -1

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_qss_file_not_found_handling(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test handling when QSS file is not found."""
        # Mock file not found
        mock_exists.return_value = False

        # Should handle gracefully and not raise error
        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Verify that the fallback theme was applied instead
        assert app is not None
        assert "background-color" in app.styleSheet()

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_empty_qss_file_handling(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test handling of empty QSS file."""
        # Mock empty QSS file
        mock_exists.return_value = True
        mock_read_text.return_value = ""

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Should handle empty stylesheet gracefully
        assert app.styleSheet() == ""

    @patch("src.spectrum_weaver.Path.exists")
    @patch("src.spectrum_weaver.Path.read_text")
    def test_layout_margins_configuration(
        self, mock_read_text: Mock, mock_exists: Mock, qtbot: QtBot
    ) -> None:
        """Test that layout margins are configured correctly."""
        # Mock the QSS file existence and reading
        mock_exists.return_value = True
        mock_read_text.return_value = "/* test styles */"

        app = SpectrumWeaver()
        qtbot.addWidget(app)

        # Check specific margin values
        margins = app.hBoxLayout.contentsMargins()
        assert margins.left() == 16
        assert margins.top() == 48
        assert margins.right() == 16
        assert margins.bottom() == 16
