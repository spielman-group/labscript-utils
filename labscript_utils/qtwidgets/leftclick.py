#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/leftclick.py                           #
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


class LeftClickMixin:
    """Mixin for an item view that signals a left click on an item.

    List it before the view's Qt base class. `leftClicked(index)` is emitted
    when the left button is pressed and released on the same valid index, and
    `doubleLeftClicked(index)` as well when that click was the second of a
    double click. A subclass cancels a click by setting `_pressed_index` to
    None before calling `mouseReleaseEvent`.
    """

    leftClicked = Signal(QtCore.QModelIndex)
    doubleLeftClicked = Signal(QtCore.QModelIndex)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pressed_index = None
        self._double_click = False

    def mousePressEvent(self, event):
        # Taken first, as a press can resize its row:
        index = self.indexAt(event.position().toPoint())
        result = super().mousePressEvent(event)
        if event.button() == QtCore.Qt.MouseButton.LeftButton and index.isValid():
            self._pressed_index = index
        return result

    def leaveEvent(self, event):
        result = super().leaveEvent(event)
        self._pressed_index = None
        self._double_click = False
        return result

    def mouseDoubleClickEvent(self, event):
        # The left click is emitted for the second click of a double click too.
        result = super().mouseDoubleClickEvent(event)
        index = self.indexAt(event.position().toPoint())
        if event.button() == QtCore.Qt.MouseButton.LeftButton and index.isValid():
            self._pressed_index = index
            self._double_click = True
        return result

    def mouseReleaseEvent(self, event):
        result = super().mouseReleaseEvent(event)
        index = self.indexAt(event.position().toPoint())
        left = event.button() == QtCore.Qt.MouseButton.LeftButton
        if left and index.isValid() and index == self._pressed_index:
            self.leftClicked.emit(index)
            if self._double_click:
                self.doubleLeftClicked.emit(index)
        self._pressed_index = None
        self._double_click = False
        return result


class TreeView(LeftClickMixin, QtWidgets.QTreeView):
    """A QTreeView that emits leftClicked and doubleLeftClicked."""


class TableView(LeftClickMixin, QtWidgets.QTableView):
    """A QTableView that emits leftClicked and doubleLeftClicked."""
