"""A module containing the SpectrumAnalyzer class for real-time audio spectrum analysis."""

import logging
import queue
import threading
from typing import Any, Callable, Optional

import numpy as np

from .audio_io import get_audio_info, iter_mono_chunks

logger = logging.getLogger(__name__)

class SpectrumAnalyzer:
    """
    A streaming spectrum analyzer that processes audio in chunks and computes linear FFT in real-time.
    This class uses threading to read audio data and perform FFT calculations concurrently.
    It supports a callback mechanism to return FFT results for each frame, allowing for real-time visualization.
    The analyzer adapts its hop length to keep the total number of frames bounded (~1,000 to ~3,000 frames),
    preventing memory exhaustion and ensuring high-speed analysis for long recordings at any sample rate.
    """

    def __init__(self, path: str, callback: Callable[[Any, np.ndarray], None],
                 fft_size: int = 2048, hop_length: Optional[int] = None, batch_size: int = 16):
        """
        Initialize the streaming spectrum analyzer.

        Args:
            path: Path to audio file
            callback: Function to call with (frame_indices, fft_magnitudes_db) for each batch
                of FFT results; called once with (-1, empty) when processing finishes.
            fft_size: Size of FFT window (power of 2)
            hop_length: Number of samples between successive frames (auto-calculated if None)
            batch_size: Number of frames to process in each batch
        """
        self.path = path
        self.callback = callback
        self.fft_size = fft_size
        self._explicit_hop_length = hop_length
        self.hop_length = hop_length or fft_size // 4
        self.batch_size = batch_size

        # Audio properties
        self.sample_rate: Optional[int] = None
        self.duration: Optional[float] = None
        self.total_samples: Optional[int] = None

        # Processing state
        self.is_running = False
        self.is_finished = False
        self.error: Optional[str] = None
        self._stop_event = threading.Event()

        # Threads
        self._reader_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None

        # Thread communication
        self._audio_queue: queue.Queue = queue.Queue(maxsize=10)

        # Pre-compute Hann window (symmetric, matches scipy.signal.windows.hann)
        n = np.arange(self.fft_size)
        self._window = 0.5 - 0.5 * np.cos(2.0 * np.pi * n / (self.fft_size - 1))
        self._freq_bins: Optional[np.ndarray] = None

    def start(self) -> dict[str, Any]:
        """
        Start the streaming analysis.

        Returns:
            Dict containing audio metadata
        """
        if self.is_running:
            raise RuntimeError("Analyzer is already running")

        try:
            info = get_audio_info(self.path)
            self.sample_rate = info.sample_rate
            self.duration = info.duration
            self.total_samples = int(self.duration * self.sample_rate)

            # Adapt hop length based on duration and sample rate to keep frames bounded
            if self._explicit_hop_length is None:
                target_frames = min(max(int(self.duration * 30), 1000), 3000)
                self.hop_length = max(self.fft_size // 4, self.total_samples // target_frames)

            # Linear FFT frequency bins spanning from 0 Hz to Nyquist (sample_rate / 2)
            frequencies = np.fft.rfftfreq(self.fft_size, 1 / self.sample_rate)
            self._freq_bins = frequencies
        except Exception as e:
            raise RuntimeError(f"Failed to load audio metadata: {e}")

        # Start threads
        self.is_running = True
        self.is_finished = False
        self._stop_event.clear()

        self._reader_thread = threading.Thread(target=self._reader_worker, daemon=True)
        self._worker_thread = threading.Thread(target=self._fft_worker, daemon=True)

        self._reader_thread.start()
        self._worker_thread.start()

        return {
            'sample_rate': self.sample_rate,
            'duration': self.duration,
            'total_samples': self.total_samples,
            'fft_size': self.fft_size,
            'hop_length': self.hop_length,
            'frequencies': frequencies,
            'num_time_frames': (self.total_samples - self.fft_size) // self.hop_length + 1
        }

    def stop(self) -> None:
        """Stop the streaming analysis."""
        if not self.is_running:
            return

        self._stop_event.set()
        self.is_running = False

        # Wait for threads to finish
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2.0)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def _put_batch(self, indices: list[int], frames: np.ndarray) -> None:
        """Put a batch into the queue, retrying until there is space or stop is requested."""
        while not self._stop_event.is_set():
            try:
                self._audio_queue.put((indices, frames), timeout=1.0)
                return
            except queue.Full:
                continue

    def _put_sentinel(self) -> None:
        """Put the end-of-stream sentinel into the queue without blocking forever."""
        while not self._stop_event.is_set():
            try:
                self._audio_queue.put(None, timeout=1.0)
                return
            except queue.Full:
                continue

    def _reader_worker(self) -> None:
        """
        Reader thread that decodes audio in chunks and frames it with a zero-copy
        sliding window, feeding batches of frames to the FFT worker.
        """
        try:
            chunk_size = self.hop_length * 50  # Process 50 frames at a time
            carry = np.zeros(0, dtype=np.float32)
            frame_index = 0
            pending_indices: list[int] = []
            pending_frames: list[np.ndarray] = []

            for mono in iter_mono_chunks(self.path, chunk_size):
                if self._stop_event.is_set():
                    return
                data = np.concatenate([carry, mono]) if carry.size else mono
                n_frames = (data.size - self.fft_size) // self.hop_length + 1
                if n_frames > 0:
                    # strided view: zero-copy framing, then one copy per batch
                    view = np.lib.stride_tricks.sliding_window_view(
                        data[: (n_frames - 1) * self.hop_length + self.fft_size], self.fft_size
                    )[:: self.hop_length]
                    carry = data[n_frames * self.hop_length :]
                    for frame in view:
                        pending_indices.append(frame_index)
                        pending_frames.append(frame)
                        frame_index += 1
                        if len(pending_frames) >= self.batch_size:
                            self._put_batch(pending_indices, np.stack(pending_frames))
                            pending_indices, pending_frames = [], []
                else:
                    carry = data

            if pending_frames and not self._stop_event.is_set():
                self._put_batch(pending_indices, np.stack(pending_frames))
            self._put_sentinel()
        except Exception as e:
            self.error = f"Reader thread error: {e}"
            logger.error(self.error)
            self._put_sentinel()

    def _fft_worker(self) -> None:
        """
        Worker thread that performs FFT calculations and calls the callback.
        Processes batches of frames for vectorized FFT and dB conversion.
        """
        try:
            while True:
                try:
                    item = self._audio_queue.get(timeout=0.5)
                except queue.Empty:
                    if self._stop_event.is_set():
                        return
                    continue
                if item is None:
                    return
                frame_indices, audio_frames = item
                # audio_frames: shape (batch, fft_size)
                windowed = audio_frames * self._window
                power = np.abs(np.fft.rfft(windowed, axis=1)) ** 2
                power = power / (self.fft_size * self.fft_size)
                power = np.maximum(power, 1e-12)
                magnitudes_db = 10.0 * np.log10(power)
                self.callback(frame_indices, magnitudes_db)
        except Exception as e:
            self.error = f"FFT worker thread error: {e}"
            logger.error(self.error)
        finally:
            self.is_finished = True
            # Notify that processing is complete (only if not stopped)
            if not self._stop_event.is_set():
                try:
                    self.callback(-1, np.array([]))
                except Exception:
                    pass
