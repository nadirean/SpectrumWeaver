"""A module containing the custom title bar for the SpectrumWeaver application."""

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QSpacerItem
from qframelesswindow import TitleBar

if TYPE_CHECKING:
    from spectrum_weaver import SpectrumWeaver


class CustomTitleBar(TitleBar):
    """
    Custom title bar for the application window.
    This class inherits from TitleBar and customizes the title bar
    by removing the default buttons and adding a custom icon and title label.
    It also sets up a layout for the title bar and handles the
    window icon and title changes. minBtn and maxBtn can be optionally disabled.
    """

    def __init__(self, parent: "SpectrumWeaver", show_min_max: bool = True) -> None:
        super().__init__(parent)

        self.setFixedHeight(48)
        self.setContentsMargins(0, 0, 0, 0)

        # Remove default buttons
        self.hBoxLayout.removeWidget(self.minBtn)
        self.hBoxLayout.removeWidget(self.maxBtn)
        self.hBoxLayout.removeWidget(self.closeBtn)

        # Add window icon. Hidden when the window has no icon, and collapsed
        # so it does not reserve space in dialog title bars.
        self.iconLabel = QLabel(self)
        self.iconLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._leading_spacer = QSpacerItem(
            8, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        self.hBoxLayout.insertSpacerItem(0, self._leading_spacer)
        self.hBoxLayout.insertWidget(
            1,
            self.iconLabel,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self.window().windowIconChanged.connect(self._set_icon)
        self._set_icon(self.window().windowIcon())

        # Add title label
        self.titleLabel = QLabel(self)
        self.titleLabel.setFixedHeight(40)
        self.titleLabel.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.hBoxLayout.insertWidget(
            2,
            self.titleLabel,
            0,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self.titleLabel.setObjectName("titleLabel")
        self.window().windowTitleChanged.connect(self._set_title)

        self.buttonLayout = QHBoxLayout()
        self.buttonLayout.setSpacing(0)
        self.buttonLayout.setContentsMargins(0, 0, 0, 0)
        if show_min_max:
            self.buttonLayout.addWidget(self.minBtn)
            self.buttonLayout.addWidget(self.maxBtn)
        else:
            self.minBtn.hide()
            self.maxBtn.hide()
        self.buttonLayout.addWidget(self.closeBtn)

        self.hBoxLayout.addLayout(self.buttonLayout, 0)
        self.hBoxLayout.setAlignment(self.buttonLayout, Qt.AlignmentFlag.AlignTop)

    def _set_title(self, title: str) -> None:
        self.titleLabel.setText(title)
        self.titleLabel.adjustSize()

    def _set_icon(self, icon: QIcon) -> None:
        if icon.isNull():
            self.iconLabel.clear()
            self.iconLabel.hide()
            self.iconLabel.setFixedSize(0, 0)
            self._leading_spacer.changeSize(
                16, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
            )
            self.hBoxLayout.invalidate()
            return
        self.iconLabel.setFixedSize(40, 40)
        self.iconLabel.show()
        self._leading_spacer.changeSize(
            8, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum
        )
        self.hBoxLayout.invalidate()
        pixmap = icon.pixmap(QSize(36, 36))
        self.iconLabel.setPixmap(
            pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
