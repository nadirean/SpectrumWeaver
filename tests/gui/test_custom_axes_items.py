"""Tests for the custom axis items module."""

import numpy as np
import pyqtgraph as pg
from pytestqt.qtbot import QtBot

from src.gui.custom_axes_items import TimeAxisItem, FreqAxisItem


def make_freq_axis(centers) -> FreqAxisItem:
    """Create a FreqAxisItem with a frequency map set from a list of centers."""
    axis = FreqAxisItem(orientation="left")
    axis.set_frequency_map(np.asarray(centers, dtype=float), float(centers[-1]))
    return axis


def tick_values_for(centers, row_indices) -> list[float]:
    """Data-space tick values that map to the given row indices."""
    freq_max = float(centers[-1])
    n = len(centers)
    return [i / (n - 1) * freq_max for i in row_indices]


class TestTimeAxisItem:
    """Test cases for the TimeAxisItem class."""

    def test_time_axis_item_initialization(self, qtbot: QtBot) -> None:
        """Test that TimeAxisItem can be initialized."""
        axis = TimeAxisItem(orientation="bottom")
        assert isinstance(axis, pg.AxisItem)
        assert isinstance(axis, TimeAxisItem)

    def test_tick_strings_formatting(self, qtbot: QtBot) -> None:
        """Test that tick strings are formatted correctly for time display."""
        axis = TimeAxisItem(orientation="bottom")

        # Test various time values
        test_values = [0, 30, 60, 90, 120, 150, 3600, 3661]
        expected = ["0:00", "0:30", "1:00", "1:30", "2:00", "2:30", "60:00", "61:01"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_fractional_seconds(self, qtbot: QtBot) -> None:
        """Test tick string formatting with fractional seconds."""
        axis = TimeAxisItem(orientation="bottom")

        # Test fractional values (should be truncated to integers)
        test_values = [0.5, 30.7, 59.9, 120.1]
        expected = ["0:00", "0:30", "0:59", "2:00"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_large_values(self, qtbot: QtBot) -> None:
        """Test tick string formatting with large time values."""
        axis = TimeAxisItem(orientation="bottom")

        # Test large values
        test_values = [7200, 86400]  # 2 hours, 24 hours
        expected = ["120:00", "1440:00"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_negative_values(self, qtbot: QtBot) -> None:
        """Test tick string formatting with negative values."""
        axis = TimeAxisItem(orientation="bottom")

        # Test negative values
        test_values = [-30, -60]
        expected = ["-0:30", "-1:00"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected


class TestFreqAxisItem:
    """Test cases for the FreqAxisItem class."""

    def test_freq_axis_item_initialization(self, qtbot: QtBot) -> None:
        """Test that FreqAxisItem can be initialized."""
        axis = FreqAxisItem(orientation="left")
        assert isinstance(axis, pg.AxisItem)
        assert isinstance(axis, FreqAxisItem)

    def test_tick_strings_formatting_hz(self, qtbot: QtBot) -> None:
        """Test that tick strings are formatted correctly for frequency in Hz."""
        centers = [0, 100, 500, 999, 22050]
        axis = make_freq_axis(centers)

        test_values = tick_values_for(centers, [0, 1, 2, 3])
        expected = ["0 Hz", "100 Hz", "500 Hz", "999 Hz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_formatting_khz(self, qtbot: QtBot) -> None:
        """Test that tick strings are formatted correctly for frequency in kHz."""
        centers = [1000, 2000, 5500, 22000]
        axis = make_freq_axis(centers)

        test_values = tick_values_for(centers, list(range(len(centers))))
        expected = ["1.0 kHz", "2.0 kHz", "5.5 kHz", "22.0 kHz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_zero(self, qtbot: QtBot) -> None:
        """Test tick string formatting with zero frequency."""
        centers = [0, 1000]
        axis = make_freq_axis(centers)

        test_values = tick_values_for(centers, [0])
        expected = ["0 Hz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_fractional_khz(self, qtbot: QtBot) -> None:
        """Test tick string formatting with fractional kHz values."""
        centers = [1500, 2300, 8820]
        axis = make_freq_axis(centers)

        test_values = tick_values_for(centers, list(range(len(centers))))
        expected = ["1.5 kHz", "2.3 kHz", "8.8 kHz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_mixed_values(self, qtbot: QtBot) -> None:
        """Test tick string formatting with mixed Hz and kHz values."""
        centers = [0, 250, 500, 1000, 2000, 11025, 22000]
        axis = make_freq_axis(centers)

        test_values = tick_values_for(centers, list(range(len(centers))))
        expected = ["0 Hz", "250 Hz", "500 Hz", "1.0 kHz", "2.0 kHz", "11.0 kHz", "22.0 kHz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_precision(self, qtbot: QtBot) -> None:
        """Test that tick values map precisely to their row frequencies."""
        centers = [123, 456, 789]
        axis = make_freq_axis(centers)

        test_values = tick_values_for(centers, list(range(len(centers))))
        expected = ["123 Hz", "456 Hz", "789 Hz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected
