"""Tests for the custom axis items module."""

import pyqtgraph as pg
from pytestqt.qtbot import QtBot

from src.gui.custom_axes_items import FreqAxisItem, TimeAxisItem


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

    def test_boundary_ticks_included(self, qtbot: QtBot) -> None:
        """Test that 0:00 and exact duration ticks are always included (Spek ruler behavior)."""
        duration = 2540.0  # 42:20
        axis = TimeAxisItem(orientation="bottom", duration=duration)
        ticks = axis.tickValues(0, duration, 800)
        assert len(ticks) == 1
        major_ticks = ticks[0][1]
        assert 0.0 in major_ticks
        assert duration in major_ticks

    def test_time_boundary_labels_in_draw_specs(self, qtbot: QtBot) -> None:
        """Test that 0:00 and duration labels are not dropped by generateDrawSpecs."""
        from PySide6.QtGui import QPainter, QPicture
        duration = 2540.0
        plot = pg.PlotWidget(axisItems={"bottom": TimeAxisItem(orientation="bottom")})
        qtbot.addWidget(plot)
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.resize(800, 400)
        bottom = plot.getAxis("bottom")
        bottom.set_duration(duration)
        plot.setXRange(0, duration, padding=0)

        pic = QPicture()
        p = QPainter(pic)
        specs = bottom.generateDrawSpecs(p)
        p.end()

        labels = [t[2] for t in specs[2]]
        assert "0:00" in labels
        assert "42:20" in labels


class TestFreqAxisItem:
    """Test cases for the FreqAxisItem class."""

    def test_freq_axis_item_initialization(self, qtbot: QtBot) -> None:
        """Test that FreqAxisItem can be initialized."""
        axis = FreqAxisItem(orientation="left")
        assert isinstance(axis, pg.AxisItem)
        assert isinstance(axis, FreqAxisItem)

    def test_tick_strings_formatting_hz(self, qtbot: QtBot) -> None:
        """Test that tick strings are formatted correctly for frequency in Hz."""
        axis = FreqAxisItem(orientation="left")

        test_values = [100, 200, 500]
        expected = ["100 Hz", "200 Hz", "500 Hz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_formatting_khz(self, qtbot: QtBot) -> None:
        """Test that tick strings are formatted correctly for frequency in kHz."""
        axis = FreqAxisItem(orientation="left")

        test_values = [1000, 2000, 5500, 22000]
        expected = ["1 kHz", "2 kHz", "5.5 kHz", "22 kHz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_zero(self, qtbot: QtBot) -> None:
        """Test tick string formatting at the bottom of the axis (0 Hz)."""
        axis = FreqAxisItem(orientation="left")

        test_values = [0.0]
        expected = ["0 kHz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_with_fractional_khz(self, qtbot: QtBot) -> None:
        """Test tick string formatting with fractional kHz values."""
        axis = FreqAxisItem(orientation="left")

        test_values = [1500, 2300, 8820]
        expected = ["1.5 kHz", "2.3 kHz", "8.82 kHz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_tick_strings_precision(self, qtbot: QtBot) -> None:
        """Test that fractional Hz below 1 kHz round to whole Hz."""
        axis = FreqAxisItem(orientation="left")

        test_values = [123, 456, 789]
        expected = ["123 Hz", "456 Hz", "789 Hz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_linear_tick_values_192khz(self, qtbot: QtBot) -> None:
        """Test linear ticks for 192 kHz audio (Nyquist 96 kHz)."""
        axis = FreqAxisItem(orientation="left", nyquist=96000.0)
        ticks = axis.tickValues(0, 96000.0, 250)
        major = ticks[0][1]

        # Should match Spek: [0, 20k, 40k, 60k, 80k, 96k]
        assert major == [0.0, 20000.0, 40000.0, 60000.0, 80000.0, 96000.0]

    def test_linear_tick_values_96khz(self, qtbot: QtBot) -> None:
        """Test linear ticks for 96 kHz audio (Nyquist 48 kHz)."""
        axis = FreqAxisItem(orientation="left", nyquist=48000.0)
        ticks = axis.tickValues(0, 48000.0, 250)
        major = ticks[0][1]

        assert major == [0.0, 10000.0, 20000.0, 30000.0, 40000.0, 48000.0]

    def test_linear_tick_values_44khz(self, qtbot: QtBot) -> None:
        """Test linear ticks for 44.1 kHz audio (Nyquist 22.05 kHz)."""
        axis = FreqAxisItem(orientation="left", nyquist=22050.0)
        ticks = axis.tickValues(0, 22050.0, 250)
        major = ticks[0][1]

        assert major == [0.0, 5000.0, 10000.0, 15000.0, 20000.0, 22050.0]

    def test_linear_tick_strings_formatting(self, qtbot: QtBot) -> None:
        """Test linear tick string formatting with clean kHz labels."""
        axis = FreqAxisItem(orientation="left")
        test_values = [0.0, 20000.0, 40000.0, 48000.0, 96000.0, 22050.0, 500.0]
        expected = ["0 kHz", "20 kHz", "40 kHz", "48 kHz", "96 kHz", "22.05 kHz", "500 Hz"]

        result = axis.tickStrings(test_values, scale=1, spacing=1)
        assert result == expected

    def test_set_nyquist(self, qtbot: QtBot) -> None:
        """Test dynamically setting nyquist frequency."""
        axis = FreqAxisItem(orientation="left")
        axis.set_nyquist(96000.0)
        assert axis.nyquist == 96000.0

    def test_freq_boundary_labels_in_draw_specs(self, qtbot: QtBot) -> None:
        """Test that 0 kHz and Nyquist labels are not dropped by generateDrawSpecs."""
        from PySide6.QtGui import QPainter, QPicture
        plot = pg.PlotWidget(axisItems={"left": FreqAxisItem(orientation="left")})
        qtbot.addWidget(plot)
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.resize(800, 400)
        left = plot.getAxis("left")
        left.set_nyquist(96000.0)
        plot.setYRange(0, 96000.0, padding=0)

        pic = QPicture()
        p = QPainter(pic)
        specs = left.generateDrawSpecs(p)
        p.end()

        labels = [t[2] for t in specs[2]]
        assert "0 kHz" in labels
        assert "96 kHz" in labels
