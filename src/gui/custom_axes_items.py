"""A module defining custom axis items for PyQtGraph plots."""

import numpy as np
import pyqtgraph as pg


class TimeAxisItem(pg.AxisItem):
    """Custom axis item for displaying time in minutes and seconds format."""
    def tickStrings(self, values, scale, spacing):
        result = []
        for val in values:
            if val < 0:
                # Handle negative values
                abs_val = abs(val)
                minutes = int(abs_val // 60)
                seconds = int(abs_val % 60)
                result.append(f"-{minutes}:{seconds:02d}")
            else:
                minutes = int(val // 60)
                seconds = int(val % 60)
                result.append(f"{minutes}:{seconds:02d}")
        return result


class FreqAxisItem(pg.AxisItem):
    """
    Linear axis whose ticks are labelled with the true (log-spaced) frequency
    centers of the spectrogram rows. Rows are drawn uniformly, so the y value of
    a tick is mapped through the row index to the corresponding bin center.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.freq_centers: np.ndarray | None = None
        self.freq_max = 22050.0

    def set_frequency_map(self, centers: np.ndarray, freq_max: float) -> None:
        """Set the row-center frequencies used for tick labels."""
        self.freq_centers = centers
        self.freq_max = freq_max

    def _value_to_freq(self, value: float) -> float:
        if self.freq_centers is None or self.freq_centers.size == 0:
            return 0.0
        n = self.freq_centers.size
        row = int(round(value / self.freq_max * (n - 1)))
        row = max(0, min(n - 1, row))
        return float(self.freq_centers[row])

    def tickStrings(self, values, scale, spacing):
        out = []
        for val in values:
            freq = self._value_to_freq(val)
            if freq >= 1000:
                out.append(f"{freq / 1000:.1f} kHz")
            else:
                out.append(f"{freq:.0f} Hz")
        return out
