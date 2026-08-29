"""A module containing CustomContextMenu class for spectrum viewer actions."""

import os
from typing import Optional, Callable

import numpy as np
from pyqtgraph import colormap
from PySide6.QtCore import Qt
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import (
    QMenu,
    QWidget,
    QFileDialog,
    QTableWidget,
    QLabel,
    QComboBox,
    QTableWidgetItem,
    QVBoxLayout,
    QCheckBox,
)

from .custom_title_bar import CustomTitleBar


def _format_size(num_bytes: int) -> str:
    """Human-readable file size."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


class CustomContextMenu:
    """
    A reusable context menu for spectrum viewer actions.
    Handles export and details logic directly.
    """

    def __init__(
        self,
        parent: Optional[QWidget],
        plot_widget,
        image_item,
        colorbar,
        audio_path: str,
        spectrogram_data: Optional[np.ndarray],
        metadata: dict,
        settings_changed_callback: Optional[Callable] = None,
    ):
        self.parent = parent
        self.plot_widget = plot_widget
        self.image_item = image_item
        self.colorbar = colorbar
        self.audio_path = audio_path
        self.spectrogram_data = spectrogram_data
        self.metadata = metadata
        self.settings_changed_callback = settings_changed_callback
        self._show_grid = True  # Default state, can be loaded from config if needed
        self._colormap = "viridis"  # Default colormap
        self._batch_size = 16  # Default batch size

    def exec(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self.parent)
        menu.addSection("Spectrogram")
        export_action = menu.addAction("Export spectrogram to PNG")
        details_action = menu.addAction("Show details")
        settings_action = menu.addAction("Settings")
        action = menu.exec(event.globalPos())

        if action == export_action:
            self._export_spectrogram_png()
        elif action == details_action:
            self._show_details_dialog()
        elif action == settings_action:
            self._show_settings_dialog()

    def _export_spectrogram_png(self):
        """Export the spectrogram as a PNG file."""
        if self.spectrogram_data is None:
            return

        name = (
            os.path.basename(self.audio_path).split(".")[0]
            if self.audio_path
            else "spectrogram"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, "Export Spectrogram", f"{name}.png", "PNG Files (*.png)"
        )

        if not file_path:
            return

        qimg_item = self.image_item.getPixmap()
        if qimg_item is None:
            return
        qimg = qimg_item.toImage()
        if qimg is None:
            return

        # Flip the image vertically to match the expected orientation
        qimg_flipped = qimg.mirrored(False, True)
        qimg_flipped.save(file_path)

    def _show_details_dialog(self):
        """Show a dialog with audio file details."""
        if not self.audio_path or not os.path.isfile(self.audio_path):
            return

        # Attempt to read metadata using Mutagen (imported lazily - only needed here)
        try:
            from mutagen import File as MutagenFile

            mf = MutagenFile(self.audio_path, easy=True)
            mf_raw = MutagenFile(self.audio_path)
        except Exception:
            mf = None
            mf_raw = None

        # Prepare details to display
        details = []
        ext = os.path.splitext(self.audio_path)[1][1:].upper()
        details.append(("File name", os.path.basename(self.audio_path)))
        details.append(("Format", ext))

        info = getattr(mf_raw, "info", None) if mf_raw is not None else None
        duration = getattr(info, "length", None) or self.metadata.get("duration", None)
        if duration:
            m, s = divmod(int(duration), 60)
            details.append(("Duration", f"{m}:{s:02d}"))

        sr = getattr(info, "sample_rate", None) or self.metadata.get(
            "sample_rate", None
        )
        if sr:
            details.append(("Sample rate", f"{sr} Hz"))

        br = getattr(info, "bitrate", None)
        if br:
            details.append(("Bitrate", f"{br // 1000} kbps"))

        ch = getattr(info, "channels", None)
        if ch:
            details.append(("Channels", str(ch)))

        codec = getattr(info, "codec", None)
        if codec:
            details.append(("Codec", str(codec)))

        bits = getattr(info, "bits_per_sample", None)
        if bits:
            details.append(("Bits/sample", str(bits)))

        try:
            size = os.path.getsize(self.audio_path)
            details.append(("File size", _format_size(size)))
        except Exception:
            pass

        if mf and hasattr(mf, "tags") and mf.tags:
            for tag in (
                "title",
                "artist",
                "album",
                "date",
                "tracknumber",
                "genre",
                "composer",
                "albumartist",
                "comment",
            ):
                val = mf.tags.get(tag)
                if val:
                    details.append(
                        (
                            tag.capitalize(),
                            ", ".join(val) if isinstance(val, list) else str(val),
                        )
                    )

        # Create and show the details dialog
        dlg = QWidget(self.parent, Qt.Window | Qt.FramelessWindowHint)
        dlg.setObjectName("DialogPanel")

        # Hide the original dialog title bar for a custom look
        title_bar = CustomTitleBar(dlg, show_min_max=False)
        dlg.setWindowTitle("Audio Details")

        # Main layout, no margins so title bar is flush
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(title_bar)

        # Content widget with margins for the table
        content_widget = QWidget(dlg)
        content_widget.setObjectName("DialogPanel")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(12)

        table = QTableWidget(len(details), 2)
        table.setHorizontalHeaderLabels(["Parameter", "Value"])

        # Populate the table with details
        for i, (k, v) in enumerate(details):
            table.setItem(i, 0, QTableWidgetItem(str(k)))
            table.setItem(i, 1, QTableWidgetItem(str(v)))

        # Make headers occupy full width and hide the top-left corner
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setCornerButtonEnabled(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        content_layout.addWidget(table)
        content_widget.setLayout(content_layout)

        layout.addWidget(content_widget)
        dlg.setLayout(layout)
        table.setMinimumSize(460, 340)
        dlg.show()

    def on_grid_toggled(self, checked):
        """Toggle the visibility of the grid on the plot."""
        self._show_grid = checked

        # Prevent errors if plot_widget is not set yet
        if self.plot_widget is not None:
            self.plot_widget.showGrid(x=checked, y=checked)

    def on_colormap_changed(self, name):
        """Change the colormap of the image item and colorbar."""
        self._colormap = name
        cmap = colormap.get(name)

        # Only update colormap if image_item and colorbar are both set
        if self.image_item is not None and self.colorbar is not None:
            self.image_item.setColorMap(cmap)
            self.colorbar.setColorMap(cmap)

    def on_batch_size_selected(self, text):
        """Change the batch size (from the settings combo box)."""
        try:
            self.on_batch_size_changed(int(text))
        except ValueError:
            pass

    def on_batch_size_changed(self, batch_size):
        """Change the batch size for spectrum analyzer processing."""
        self._batch_size = batch_size
        # Notify parent that settings changed (requires restart of analysis)
        if self.settings_changed_callback:
            self.settings_changed_callback("batch_size", batch_size)

    def get_batch_size(self):
        """Get the current batch size setting."""
        return self._batch_size

    def _show_settings_dialog(self):
        """Show a settings dialog with a custom title bar and colormap selection."""
        dlg = QWidget(self.parent, Qt.Window | Qt.FramelessWindowHint)
        dlg.setObjectName("DialogPanel")

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Custom title bar
        title_bar = CustomTitleBar(dlg, show_min_max=False)
        dlg.setWindowTitle("Settings")
        layout.addWidget(title_bar)

        # Content widget with its own layout and margins
        content_widget = QWidget(dlg)
        content_widget.setObjectName("DialogPanel")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(12)

        # Grid visibility checkbox
        grid_checkbox = QCheckBox("Show grid on plot")
        grid_checkbox.setChecked(self._show_grid)
        grid_checkbox.toggled.connect(self.on_grid_toggled)

        # Predefined list of colormaps
        colormaps = ["viridis", "plasma", "inferno", "magma", "cividis"]

        # Predefined list of batch sizes
        batch_sizes = [4, 8, 16, 32, 64, 128]

        # Label for colormap selection
        colormap_label = QLabel("Colormap:")

        # Combo box for colormap selection
        colormap_combo = QComboBox()
        colormap_combo.addItems(colormaps)
        colormap_combo.setCurrentText(self._colormap)
        colormap_combo.currentTextChanged.connect(self.on_colormap_changed)

        # Label for batch size selection
        batch_size_label = QLabel("Batch Size:")

        # Combo box for batch size selection
        batch_size_combo = QComboBox()
        batch_size_combo.addItems([str(size) for size in batch_sizes])
        batch_size_combo.setCurrentText(str(self._batch_size))
        batch_size_combo.currentTextChanged.connect(self.on_batch_size_selected)

        # Add widgets to content layout
        content_layout.addWidget(grid_checkbox)
        content_layout.addSpacing(10)
        content_layout.addWidget(colormap_label)
        content_layout.addWidget(colormap_combo)
        content_layout.addWidget(batch_size_label)
        content_layout.addWidget(batch_size_combo)
        content_widget.setLayout(content_layout)

        # Add content widget to main layout
        layout.addWidget(content_widget)

        dlg.setLayout(layout)
        dlg.show()
