#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/themed_window.py                       #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
from qtutils.qt import QtCore, QtWidgets
from qtutils.qt.QtCore import pyqtSignal as Signal


class ThemedWindow:
    """Mixin for a window that refreshes its widgets when the theme changes.

    List it before the window's Qt base class. The window applies each child
    widget's style sheet and palette again, which complex widgets such as
    tree and table views need to follow a new theme, and then emits
    `themeChanged` for anything of the window's own that follows the theme.
    """

    themeChanged = Signal()

    def changeEvent(self, event):
        # A theme switch reaches changeEvent as PaletteChange: QWidget.event()
        # never passes ApplicationPaletteChange on to it.
        if event.type() in (
            QtCore.QEvent.Type.PaletteChange, QtCore.QEvent.Type.StyleChange
        ):
            for widget in self.findChildren(QtWidgets.QWidget):
                widget.setStyleSheet(widget.styleSheet())
                widget.setPalette(widget.palette())
            self.themeChanged.emit()
        return super().changeEvent(event)


class FirstPaintWindow:
    """Mixin for a window that emits `firstPaint` once, when it is first painted.

    List it before the window's Qt base class.
    """

    firstPaint = Signal()
    _previously_painted = False

    def paintEvent(self, event):
        result = super().paintEvent(event)
        if not self._previously_painted:
            self._previously_painted = True
            self.firstPaint.emit()
        return result
