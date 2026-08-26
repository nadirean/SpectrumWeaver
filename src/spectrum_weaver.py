"""A module containing the main application class for SpectrumWeaver."""

import logging
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QStackedWidget
from qframelesswindow import FramelessWindow

from gui.custom_title_bar import CustomTitleBar
from gui.spectrum_viewer import SpectrumViewer

logger = logging.getLogger(__name__)


def asset_path(name: str) -> Path:
    """Path to a bundled asset (works from source and from a PyInstaller bundle)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "assets" / name


class SpectrumWeaver(FramelessWindow):
    """
    Main application window for SpectrumWeaver.
    Inherits from FramelessWindow to provide a custom
    title bar and window frame. Sets up the layout and initializes
    the spectrum viewer for file handling.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setTitleBar(CustomTitleBar(self))

        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(16, 48, 16, 16)

        self.stacked_widget = QStackedWidget(self)
        self.spectrum_viewer = SpectrumViewer(self)
        self.stacked_widget.addWidget(self.spectrum_viewer)
        self.stacked_widget.setCurrentWidget(self.spectrum_viewer)

        self._init_window()
        self._set_qss()

    def _init_window(self) -> None:
        self.setWindowTitle("SpectrumWeaver")
        self.setWindowIcon(QIcon(str(asset_path("icon.png"))))

        self.hBoxLayout.addWidget(self.stacked_widget)
        self.setLayout(self.hBoxLayout)

        self.resize(960, 640)
        self.setMinimumSize(720, 480)

    def _set_qss(self) -> None:
        try:
            stylesheet_path = asset_path("styles.qss")
            if not stylesheet_path.exists():
                stylesheet_path = Path(__file__).parent / "assets" / "styles.qss"
            if stylesheet_path.exists():
                self.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))
                return
        except Exception as e:
            logger.error("Error loading stylesheet: %s", e)
        self._apply_fallback_theme()

    def _apply_fallback_theme(self) -> None:
        self.setStyleSheet("""
            QWidget {
                background-color: rgb(32, 32, 32);
                color: white;
            }
            SpectrumWeaver {
                background-color: rgb(32, 32, 32);
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    spectrum_weaver = SpectrumWeaver()
    spectrum_weaver.show()
    app.exec()
