"""Tests for the CustomTitleBar class."""

from collections.abc import Generator

import pytest
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QWidget
from pytestqt.qtbot import QtBot

from src.gui.custom_title_bar import CustomTitleBar


@pytest.fixture
def parent(qtbot: QtBot) -> Generator[QWidget, None, None]:  # noqa: ARG001
    """Fixture to create a simple parent QWidget instance."""
    # Create a parent QWidget for the CustomTitleBar
    widget = QWidget()
    yield widget

    # Cleanup
    try:
        # Close the widget if it's still open
        widget.close()
        widget.deleteLater()
    except RuntimeError:
        # The widget is already closed
        # Exception can be ignored
        pass


@pytest.fixture
def title_bar(parent: QWidget) -> CustomTitleBar:
    """Fixture to create a CustomTitleBar instance with a QWidget parent."""
    return CustomTitleBar(parent)


def test_custom_title_bar_init(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test the initialization of the CustomTitleBar."""
    assert title_bar is not None
    assert title_bar.height() == 48  # noqa: PLR2004
    assert title_bar.parent() is parent

    # Check if default buttons are removed from the main horizontal layout
    assert title_bar.minBtn.parent() is title_bar
    assert title_bar.maxBtn.parent() is title_bar
    assert title_bar.closeBtn.parent() is title_bar

    # Check they are NOT in the main hBoxLayout directly
    assert title_bar.hBoxLayout.indexOf(title_bar.minBtn) == -1
    assert title_bar.hBoxLayout.indexOf(title_bar.maxBtn) == -1
    assert title_bar.hBoxLayout.indexOf(title_bar.closeBtn) == -1

    # Check if icon and title labels are added
    assert isinstance(title_bar.iconLabel, QLabel)
    assert isinstance(title_bar.titleLabel, QLabel)
    assert title_bar.hBoxLayout.indexOf(title_bar.iconLabel) != -1
    assert title_bar.hBoxLayout.indexOf(title_bar.titleLabel) != -1
    assert title_bar.titleLabel.objectName() == "titleLabel"

    # Check if the custom button layout exists and contains the buttons
    assert hasattr(title_bar, "buttonLayout")
    assert not hasattr(title_bar, "vBoxLayout")
    assert title_bar.buttonLayout.indexOf(title_bar.minBtn) != -1
    assert title_bar.buttonLayout.indexOf(title_bar.maxBtn) != -1
    assert title_bar.buttonLayout.indexOf(title_bar.closeBtn) != -1
    assert title_bar.hBoxLayout.indexOf(title_bar.buttonLayout) != -1


def test_set_title(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test the _set_title method."""
    test_title = "Test Widget Title"

    # Simulate the parent widget title changing, which should trigger the slot
    parent.setWindowTitle(test_title)
    assert title_bar.titleLabel.text() == test_title


def test_set_icon(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test the _set_icon method."""
    # Create a dummy icon
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.red)
    test_icon = QIcon(pixmap)

    # Simulate the parent widget icon changing
    parent.setWindowIcon(test_icon)

    # Check if the iconLabel has a pixmap set
    assert not title_bar.iconLabel.isHidden()
    assert title_bar.iconLabel.size() == QSize(40, 40)
    assert title_bar.iconLabel.pixmap() is not None
    assert not title_bar.iconLabel.pixmap().isNull()
    # Icon gets scaled to 36x36 as per the implementation
    assert title_bar.iconLabel.pixmap().size() == QSize(36, 36)
    assert title_bar._leading_spacer.sizeHint().width() == 8  # noqa: PLR2004


def test_fixed_height(title_bar: CustomTitleBar) -> None:
    """Test that the title bar has the correct fixed height."""
    assert title_bar.height() == 48  # noqa: PLR2004
    assert title_bar.minimumHeight() == 48  # noqa: PLR2004
    assert title_bar.maximumHeight() == 48  # noqa: PLR2004


def test_icon_label_collapsed_without_icon(title_bar: CustomTitleBar) -> None:
    """Hidden icon must not reserve layout space on dialogs."""
    assert title_bar.iconLabel.isHidden()
    assert title_bar.iconLabel.size() == QSize(0, 0)
    assert title_bar.iconLabel.minimumSize() == QSize(0, 0)
    assert title_bar.iconLabel.maximumSize() == QSize(0, 0)
    assert title_bar._leading_spacer.sizeHint().width() == 16  # noqa: PLR2004


def test_icon_label_properties_with_icon(
    title_bar: CustomTitleBar, parent: QWidget
) -> None:
    """Test the icon label properties when a window icon is set."""
    pixmap = QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.red)
    parent.setWindowIcon(QIcon(pixmap))

    assert title_bar.iconLabel.size() == QSize(40, 40)
    assert title_bar.iconLabel.minimumSize() == QSize(40, 40)
    assert title_bar.iconLabel.maximumSize() == QSize(40, 40)


def test_button_layout_properties(title_bar: CustomTitleBar) -> None:
    """Test the button layout properties."""
    assert title_bar.buttonLayout.spacing() == 0
    assert title_bar.buttonLayout.contentsMargins().left() == 0
    assert title_bar.buttonLayout.contentsMargins().top() == 0
    assert title_bar.buttonLayout.contentsMargins().right() == 0
    assert title_bar.buttonLayout.contentsMargins().bottom() == 0


def test_button_layout_top_aligned(title_bar: CustomTitleBar) -> None:
    """Test that the control row is anchored to the top edge of the rounded frame."""
    index = title_bar.hBoxLayout.indexOf(title_bar.buttonLayout)
    assert index != -1

    item = title_bar.hBoxLayout.itemAt(index)
    assert item is not None
    assert item.alignment() & Qt.AlignmentFlag.AlignTop
    assert title_bar.buttonLayout.contentsMargins().top() == 0


def test_signal_connections(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test that signal connections work properly."""
    # Test title change signal
    initial_title = "Initial Title"
    parent.setWindowTitle(initial_title)
    assert title_bar.titleLabel.text() == initial_title

    # Test title change again
    new_title = "New Title"
    parent.setWindowTitle(new_title)
    assert title_bar.titleLabel.text() == new_title


def test_layout_widget_order(title_bar: CustomTitleBar) -> None:
    """Test the order of widgets in the main horizontal layout."""
    # The layout should have: spacing, iconLabel, titleLabel, buttonLayout
    layout = title_bar.hBoxLayout

    # Check that iconLabel comes before titleLabel, which comes before buttonLayout
    icon_index = layout.indexOf(title_bar.iconLabel)
    title_index = layout.indexOf(title_bar.titleLabel)
    buttons_index = layout.indexOf(title_bar.buttonLayout)

    assert icon_index != -1
    assert title_index != -1
    assert buttons_index != -1
    assert icon_index < title_index < buttons_index


def test_title_label_adjusts_size(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test that the title label adjusts its size when title changes."""
    # Set a short title
    short_title = "Short"
    parent.setWindowTitle(short_title)
    short_width = title_bar.titleLabel.width()

    # Set a longer title
    long_title = "This is a much longer title"
    parent.setWindowTitle(long_title)
    long_width = title_bar.titleLabel.width()

    # The width should increase for the longer title
    assert long_width >= short_width


def test_empty_title_handling(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test handling of empty title."""
    parent.setWindowTitle("")
    assert title_bar.titleLabel.text() == ""


def test_empty_icon_handling(title_bar: CustomTitleBar, parent: QWidget) -> None:
    """Test handling of empty icon."""
    empty_icon = QIcon()
    parent.setWindowIcon(empty_icon)

    # Hidden and collapsed so the title is not pushed toward the center
    assert title_bar.iconLabel.isHidden()
    assert title_bar.iconLabel.width() == 0
    assert title_bar._leading_spacer.sizeHint().width() == 16  # noqa: PLR2004
