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

from labscript_utils.qtwidgets.row_order import moved_row_order


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


class MovableRowsMixin:
    """Mixin for a view of a QStandardItemModel whose rows the user reorders.

    List it before the view's Qt base class. `rowsReordered(order)` is emitted
    after a reorder, with the new position of each row indexed by its old one.
    """

    rowsReordered = Signal(list)

    def reorder_rows(self, order):
        """Move each row to its new position, keeping the selected rows selected.

        Parameters
        ----------
        order : list of int
            The new position of each row, indexed by its old one.
        """
        model = self.model()
        selection_model = self.selectionModel()
        selected = {index.row() for index in selection_model.selectedIndexes()}
        rows = [model.takeRow(0) for _ in order]
        for row in sorted(range(len(rows)), key=order.__getitem__):
            model.appendRow(rows[row])
        for row in selected:
            selection_model.select(
                model.indexFromItem(rows[row][0]),
                QtCore.QItemSelectionModel.SelectionFlag.Select
                | QtCore.QItemSelectionModel.SelectionFlag.Rows,
            )
        self.rowsReordered.emit(order)

    def move_selected_rows(self, direction):
        """Move the selected rows ``'up'``, ``'down'``, to the ``'top'`` or the ``'bottom'``."""
        selected = {index.row() for index in self.selectionModel().selectedIndexes()}
        self.reorder_rows(moved_row_order(self.model().rowCount(), selected, direction))


class TreeView(LeftClickMixin, MovableRowsMixin, QtWidgets.QTreeView):
    """A QTreeView that emits leftClicked and doubleLeftClicked, and moves rows."""


class TableView(LeftClickMixin, MovableRowsMixin, QtWidgets.QTableView):
    """A QTableView that emits leftClicked and doubleLeftClicked, and moves rows."""
