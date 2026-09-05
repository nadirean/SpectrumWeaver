"""A streaming spectrum viewer widget that displays spectrograms in real-time."""

import threading
from typing import Any

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QContextMenuEvent,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QMouseEvent,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from analyzers.spectrum_analyzer import SpectrumAnalyzer

from .custom_axes_items import FreqAxisItem, TimeAxisItem
from .custom_context_menu import CustomContextMenu

# Display refresh interval: the spectrogram is redrawn at most this often,
# regardless of how fast frames arrive.
DISPLAY_REFRESH_MS = 33

# Plot title style: muted and small so the path does not dominate the view.
TITLE_STYLE = {"color": "#a0a0a0", "size": "11pt"}

AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac")
AUDIO_FILE_FILTER = "Audio files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac)"


class _EmptyDropPage(QWidget):
    """Placeholder shown before an audio file is loaded. Forwards drops to the viewer."""

    def __init__(self, viewer: "SpectrumViewer") -> None:
        super().__init__()
        self._viewer = viewer
        self.setObjectName("EmptyHintPage")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()

        title = QLabel("Drop an audio file here or click to browse")
        title.setObjectName("EmptyHintTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("WAV, FLAC, OGG, MP3, M4A, AAC")
        subtitle.setProperty("muted", True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        for label in (title, subtitle):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout.addStretch()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        self._viewer.dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self._viewer.dropEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._viewer._open_audio_file_dialog()
        super().mouseReleaseEvent(event)


class SpectrumViewer(QWidget):
    """
    A widget for displaying a streaming spectrogram of an audio file.

    The analyzer delivers frames in batches; rows are written into a preallocated
    array and the display is refreshed by a timer (DISPLAY_REFRESH_MS), so UI work
    does not scale with the number of frames.
    """

    # frame_indices (list), magnitudes_db (n_frames, n_bins)
    frames_received = Signal(list, np.ndarray)
    analysis_complete = Signal()

    def __init__(self, parent: QStackedWidget, path: str = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.audio_path = path
        self.analyzer: SpectrumAnalyzer = None
        self.spectrogram_data: np.ndarray = None
        self.data_lock = threading.Lock()
        self.metadata: dict = {}
        self._last_displayed_frame = 0
        self._display_dirty = False
        self._generation = 0

        # Connect signals
        self.frames_received.connect(self._on_frames_received)

        # Display refresh timer
        self._display_timer = QTimer(self)
        self._display_timer.setInterval(DISPLAY_REFRESH_MS)
        self._display_timer.timeout.connect(self._update_display)

        # UI components
        self.plot_widget = None
        self.image_item = None
        self.color_bar = None
        self.context_menu = CustomContextMenu(
            self,
            plot_widget=None,  # will be set after _setup_ui
            image_item=None,  # will be set after _setup_ui
            colorbar=None,  # will be set after _setup_ui
            audio_path=self.audio_path,
            spectrogram_data=self.spectrogram_data,
            metadata=self.metadata,
            settings_changed_callback=self._on_settings_changed,
        )

        self._setup_ui()

        # Set plot_widget and image_item references in context_menu
        self.context_menu.plot_widget = self.plot_widget
        self.context_menu.image_item = self.image_item

        if self.audio_path:
            self._start_analysis()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)

        # Custom axis items for the plot
        axis_items = {
            "bottom": TimeAxisItem(orientation="bottom"),
            "left": FreqAxisItem(orientation="left"),
        }

        # Plot widget with custom axes
        self.plot_widget = pg.PlotWidget(axisItems=axis_items)
        self.plot_widget.setBackground("#272727")

        # Consistent tick typography across both custom axes
        tick_font = QFont("Helvetica Neue")
        tick_font.setPixelSize(11)
        for axis in axis_items.values():
            axis.setStyle(tickFont=tick_font)

        # Create the image item for the spectrogram
        self.image_item = pg.ImageItem()
        self.image_item.setAutoDownsample(True)
        self.plot_widget.addItem(self.image_item)

        # Empty hint vs plot: inner stack must not inherit the window panel border
        self._empty_page = _EmptyDropPage(self)
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("ViewerContent")
        self._content_stack.addWidget(self._empty_page)
        self._content_stack.addWidget(self.plot_widget)
        main_layout.addWidget(self._content_stack)
        self._show_empty_page()

        # Configure the plot
        self.plot_widget.setLabel("left", "Frequency", color="#a0a0a0")
        self.plot_widget.setLabel("bottom", "Time", color="#a0a0a0")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.hideButtons()

        # Set initial view range
        self.plot_widget.setXRange(0, 60)
        self.plot_widget.setYRange(0, 22050.0)

        # Set color map
        cmap = pg.colormap.get("viridis")
        self.image_item.setColorMap(cmap)

        # Add color bar for dB scale
        self.color_bar = pg.ColorBarItem(
            values=(-120, 0), colorMap=cmap, label="dB", interactive=False
        )
        self.color_bar.setImageItem(
            self.image_item, insert_in=self.plot_widget.getPlotItem()
        )

        self.plot_widget.setTitle(self.audio_path or "", **TITLE_STYLE)

        # After UI is set up, update context_menu references
        if self.context_menu:
            self.context_menu.plot_widget = self.plot_widget
            self.context_menu.image_item = self.image_item
            self.context_menu.colorbar = self.color_bar

    def _show_empty_page(self) -> None:
        self._content_stack.setCurrentWidget(self._empty_page)

    def _show_plot_page(self) -> None:
        self._content_stack.setCurrentWidget(self.plot_widget)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        # Update context_menu data before showing
        self.context_menu.audio_path = self.audio_path
        self.context_menu.spectrogram_data = self.spectrogram_data
        self.context_menu.metadata = self.metadata
        self.context_menu.exec(event)

    def _configure_axes(self) -> None:
        """Configure plot axes based on audio metadata."""
        if not self.metadata:
            return

        duration = self.metadata["duration"]
        sample_rate = self.metadata.get("sample_rate", 44100)
        nyquist = float(sample_rate / 2.0)

        freq_axis = self.plot_widget.getAxis("left")
        if hasattr(freq_axis, "set_nyquist"):
            freq_axis.set_nyquist(nyquist)

        time_axis = self.plot_widget.getAxis("bottom")
        if hasattr(time_axis, "set_duration"):
            time_axis.set_duration(duration)

        # X-axis: Time (0 to duration)
        self.plot_widget.setXRange(0, duration)

        self.plot_widget.setLabel("left", "Frequency", color="#a0a0a0")
        self.plot_widget.setYRange(0, nyquist)
        self.plot_widget.setLimits(xMin=0, xMax=duration, yMin=0, yMax=nyquist)

    def _start_analysis(self) -> None:
        """Start the streaming spectrum analysis."""
        if not self.audio_path:
            return
        try:
            # Get settings from context menu
            batch_size = self.context_menu.get_batch_size() if self.context_menu else 16

            self._generation += 1
            generation = self._generation

            # Create analyzer with optimized parameters (using Hann window)
            self.analyzer = SpectrumAnalyzer(
                path=self.audio_path,
                callback=lambda idx, mags, gen=generation: self._on_fft_result_threaded(
                    idx, mags, gen
                ),
                fft_size=2048,
                hop_length=None,
                batch_size=batch_size,
            )

            # Start analysis and get metadata
            self.metadata = self.analyzer.start()

            # Initialize spectrogram data array with noise floor value
            num_time_frames = self.metadata["num_time_frames"]
            num_freq_bins = len(self.metadata["frequencies"])
            with self.data_lock:
                self.spectrogram_data = np.full(
                    (num_time_frames, num_freq_bins), -140.0, dtype=np.float32
                )
                self._last_displayed_frame = 0
            self._display_dirty = False

            # Configure plot axes based on metadata
            self._configure_axes()

            self.plot_widget.setTitle(self.audio_path, **TITLE_STYLE)

            self._display_timer.start()
            self._show_plot_page()

        except Exception as e:
            self.plot_widget.setTitle(f"Error: {str(e)}", color="#ff6b6b", size="11pt")
            self._show_plot_page()

    def _on_fft_result_threaded(
        self, frame_indices, magnitudes_db: np.ndarray, generation: int
    ) -> None:
        """
        Thread-safe callback function called by the streaming analyzer.
        This emits Qt signals to ensure UI updates happen on the main thread.
        """
        if generation != self._generation:
            return  # stale analyzer from a previous file

        if frame_indices == -1:  # End of processing signal
            try:
                QTimer.singleShot(0, self._on_analysis_complete)
            except RuntimeError:
                pass
        else:
            self.frames_received.emit(frame_indices, magnitudes_db)

    def _on_frames_received(
        self, frame_indices: list, magnitudes_db: np.ndarray
    ) -> None:
        """
        Main thread handler for FFT results.
        This is called via Qt signal from the worker thread.
        """
        with self.data_lock:
            if self.spectrogram_data is None:
                return
            n_rows = self.spectrogram_data.shape[0]
            n_bins = min(magnitudes_db.shape[1], self.spectrogram_data.shape[1])
            for row, frame_index in enumerate(frame_indices):
                if 0 <= frame_index < n_rows:
                    self.spectrogram_data[frame_index, :n_bins] = magnitudes_db[
                        row, :n_bins
                    ]
                    self._last_displayed_frame = max(
                        self._last_displayed_frame, frame_index + 1
                    )
            self._display_dirty = True

    def _update_display(self) -> None:
        """
        Update the display with new spectrogram data.
        Runs on a timer so UI work is throttled regardless of frame rate.
        """
        with self.data_lock:
            if (
                self.spectrogram_data is None
                or not self.metadata
                or not self._display_dirty
            ):
                return
            self._display_dirty = False
            current_data = self.spectrogram_data[
                : self._last_displayed_frame
            ]  # zero-copy view
            last_frame = self._last_displayed_frame
            total_frames = self.spectrogram_data.shape[0]
            duration = self.metadata["duration"]

        self.image_item.setImage(current_data, levels=(-120, 0), autoRange=False)
        time_extent = (
            duration * (last_frame / total_frames) if total_frames else duration
        )
        sample_rate = self.metadata.get("sample_rate", 44100)
        nyquist = float(sample_rate / 2.0)

        self.image_item.setRect(0, 0, time_extent, nyquist)

    def _on_analysis_complete(self) -> None:
        """Called when streaming analysis is complete."""
        self._display_timer.stop()
        with self.data_lock:
            self._display_dirty = True
        self._update_display()
        if self.analyzer and self.analyzer.error:
            QMessageBox.warning(
                self, "Analysis finished with errors", self.analyzer.error
            )
        self.analysis_complete.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Clean up when the widget is closed."""
        self._display_timer.stop()
        if self.analyzer:
            self.analyzer.stop()
        super().closeEvent(event)

    def load_audio(self, path: str) -> None:
        """Load a new audio file and reset the spectrogram viewer."""
        # Stop current analysis and timer
        self._display_timer.stop()
        if self.analyzer:
            self.analyzer.stop()
            self.analyzer = None

        with self.data_lock:
            self.spectrogram_data = None
            self._last_displayed_frame = 0
            self._display_dirty = False
        self.metadata = {}
        self.audio_path = path

        # Clear plot and update title
        self.plot_widget.setTitle(path, **TITLE_STYLE)
        self.image_item.clear()

        # Start new analysis
        self._start_analysis()

        # Ensure axes and limits are updated for new file
        self._configure_axes()

    def _open_audio_file_dialog(self) -> None:
        """Open a file picker and load the chosen audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open audio file", "", AUDIO_FILE_FILTER
        )
        if file_path:
            self.load_audio(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            # Accept only if at least one file is an audio file
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(
                    AUDIO_EXTENSIONS
                ):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(
                AUDIO_EXTENSIONS
            ):
                self.load_audio(url.toLocalFile())
                break
        event.accept()

    def _on_settings_changed(self, setting_name: str, value: Any) -> None:
        """Handle settings changes from the context menu."""
        if setting_name == "batch_size":
            # Restart analysis with new batch size if currently running
            if self.analyzer and self.analyzer.is_running:
                self._restart_analysis()

    def _restart_analysis(self) -> None:
        """Restart the spectrum analysis with current settings."""
        self._display_timer.stop()
        if self.analyzer:
            self.analyzer.stop()
            self.analyzer = None

        # Clear existing data
        with self.data_lock:
            self.spectrogram_data = None
            self._last_displayed_frame = 0
            self._display_dirty = False

        # Start new analysis
        self._start_analysis()
