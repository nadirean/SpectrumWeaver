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
    Logarithmic frequency axis for the spectrogram.

    The plot's y data space is log10(Hz), so a tick at data value ``v``
    corresponds to the frequency ``10 ** v``. Ticks are placed on a 1-2-5
    ladder per decade (100 Hz, 200 Hz, 500 Hz, 1 kHz, 2 kHz, 5 kHz, ...) and
    labelled with clean Hz/kHz strings. The axis top is the audio Nyquist
    frequency, so it adapts to the sample rate automatically.
    """

    def tickValues(self, minVal, maxVal, size):
        """Return major (decade) and minor (2x/5x) ticks on a 1-2-5 ladder."""
        lo, hi = min(minVal, maxVal), max(minVal, maxVal)
        start_decade = int(np.floor(lo))
        end_decade = int(np.ceil(hi))

        major: list[float] = []
        minor: list[float] = []
        for decade in range(start_decade, end_decade + 1):
            for mantissa in (1, 2, 5):
                value = decade + np.log10(mantissa)
                if lo <= value <= hi:
                    (major if mantissa == 1 else minor).append(value)

        return [(1.0, major), (None, minor)]

    def tickStrings(self, values, scale, spacing):
        """Format log10(Hz) tick values as clean Hz/kHz strings."""
        out = []
        for value in values:
            freq = 10.0**value
            if freq < 1000.0:
                out.append(f"{freq:.0f} Hz")
            else:
                out.append(f"{freq / 1000.0:.1f} kHz".replace(".0 kHz", " kHz"))
        return out
