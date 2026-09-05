"""A module defining custom axis items for PyQtGraph plots with Spek-accurate ruler logic."""

import pyqtgraph as pg


class TimeAxisItem(pg.AxisItem):
    """
    Time axis item with Spek-accurate ruler logic.

    Guarantees that boundary ticks (0:00 and exact audio duration) are always
    displayed, with evenly spaced intermediate ticks chosen from standard time factors.
    """

    def __init__(self, orientation: str = "bottom", duration: float | None = None, **kwargs) -> None:
        super().__init__(orientation, **kwargs)
        self.duration = duration
        self.enableAutoSIPrefix(False)

    def boundingRect(self):
        """Pad bounding rect to ensure boundary labels at 0:00 and duration are not clipped."""
        rect = super().boundingRect()
        return rect.adjusted(-50, -50, 50, 50)

    def set_duration(self, duration: float | None) -> None:
        """Set the audio duration in seconds for boundary tick placement."""
        self.duration = duration
        self.update()

    def tickValues(self, minVal, maxVal, size):
        """Calculate major ticks following Spek's ruler algorithm."""
        lo, hi = min(minVal, maxVal), max(minVal, maxVal)
        rng = hi - lo
        if rng <= 0:
            return []

        # Target label width in pixels for "00:00" with padding
        label_len = 45.0
        spacing_mult = 1.5
        px_size = max(float(size), 100.0)
        scale = px_size / rng

        time_factors = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]
        factor = time_factors[-1]
        for f in time_factors:
            if scale * f >= spacing_mult * label_len:
                factor = f
                break

        max_units = int(round(self.duration)) if self.duration is not None else int(round(hi))
        min_units = 0

        ticks: list[float] = []
        if lo <= min_units <= hi:
            ticks.append(float(min_units))
        if self.duration is not None and lo <= self.duration <= hi:
            ticks.append(float(self.duration))

        # Intermediate ticks
        if factor > 0:
            curr = min_units + factor
            while curr < max_units:
                # Stop if approaching max_units to avoid visual collision
                if scale * (max_units - curr) < label_len * 1.2:
                    break
                if lo <= curr <= hi:
                    ticks.append(float(curr))
                curr += factor

        ticks = sorted(list(dict.fromkeys(ticks)))
        return [(float(factor), ticks)]

    def tickStrings(self, values, scale, spacing):
        """Format seconds into M:SS matching Spek."""
        result = []
        for val in values:
            abs_val = abs(val)
            minutes = int(abs_val // 60)
            seconds = int(abs_val % 60)
            sign = "-" if val < 0 else ""
            result.append(f"{sign}{minutes}:{seconds:02d}")
        return result


class FreqAxisItem(pg.AxisItem):
    """
    Linear frequency axis for the spectrogram with Spek-accurate ruler logic.

    Guarantees that boundary ticks (0 kHz and the exact Nyquist frequency) are
    always displayed at the bottom and top of the axis, with intermediate ticks
    chosen from clean kHz factors.
    """

    def __init__(self, orientation: str = "left", nyquist: float | None = None, **kwargs) -> None:
        super().__init__(orientation, **kwargs)
        self.nyquist = nyquist
        self.enableAutoSIPrefix(False)
        self.setWidth(60)

    def boundingRect(self):
        """Pad bounding rect to ensure boundary labels at 0 kHz and Nyquist are not clipped."""
        rect = super().boundingRect()
        return rect.adjusted(-50, -50, 50, 50)

    def set_nyquist(self, nyquist: float | None) -> None:
        """Set the Nyquist frequency in Hz for ceiling tick placement."""
        self.nyquist = nyquist
        self.update()

    def tickValues(self, minVal, maxVal, size):
        """Calculate major ticks following Spek's frequency ruler algorithm."""
        lo, hi = min(minVal, maxVal), max(minVal, maxVal)
        rng = hi - lo
        if rng <= 0:
            return []

        # Target label height in pixels with padding
        label_len = 16.0
        spacing_mult = 2.8
        px_size = max(float(size), 100.0)
        scale = px_size / rng

        freq_factors = [500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
        factor = freq_factors[-1]
        for f in freq_factors:
            if scale * f >= spacing_mult * label_len:
                factor = f
                break

        max_units = int(round(self.nyquist)) if self.nyquist is not None else int(round(hi))
        min_units = 0

        ticks: list[float] = []
        if lo <= min_units <= hi:
            ticks.append(float(min_units))
        if self.nyquist is not None and lo <= self.nyquist <= hi:
            ticks.append(float(self.nyquist))

        # Intermediate ticks
        if factor > 0:
            curr = min_units + factor
            while curr < max_units:
                # Stop if approaching max_units to avoid visual collision
                if scale * (max_units - curr) < label_len * 1.4:
                    break
                if lo <= curr <= hi:
                    ticks.append(float(curr))
                curr += factor

        ticks = sorted(list(dict.fromkeys(ticks)))
        return [(float(factor), ticks)]

    def tickStrings(self, values, scale, spacing):
        """Format tick values as clean Hz/kHz strings matching Spek."""
        out = []
        for val in values:
            if abs(val) < 1.0:
                out.append("0 kHz")
            elif val < 1000.0:
                out.append(f"{val:.0f} Hz")
            else:
                khz = val / 1000.0
                if abs(khz - round(khz)) < 1e-3:
                    out.append(f"{int(round(khz))} kHz")
                elif abs(khz * 10 - round(khz * 10)) < 1e-3:
                    out.append(f"{khz:.1f} kHz")
                else:
                    out.append(f"{khz:.2f} kHz".rstrip("0").rstrip("."))
        return out
