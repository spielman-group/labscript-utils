#####################################################################
#                                                                   #
# /tests/test_row_order.py                                          #
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
"""Moving the selected rows of a list, as runviewer's and lyse's buttons do."""
import pytest
from qtutils.qt import QtCore, QtGui, QtWidgets

from labscript_utils.qtwidgets.leftclick import TreeView
from labscript_utils.qtwidgets.row_order import moved_row_order


_qapplication = None


def rows_after(n_rows, selected, direction):
    """The old rows, listed in their new order."""
    order = moved_row_order(n_rows, selected, direction)
    return sorted(range(n_rows), key=order.__getitem__)


@pytest.mark.parametrize(
    'selected, direction, rows',
    [
        ({2, 3}, 'up', [0, 2, 3, 1, 4]),
        ({0, 1, 3}, 'up', [0, 1, 3, 2, 4]),
        ({1, 2}, 'down', [0, 3, 1, 2, 4]),
        ({2, 4}, 'down', [0, 1, 3, 2, 4]),
        ({1, 3}, 'top', [1, 3, 0, 2, 4]),
        ({1, 3}, 'bottom', [0, 2, 4, 1, 3]),
    ],
)
def test_selected_rows_move_together_and_stop_at_the_ends(selected, direction, rows):
    assert rows_after(5, selected, direction) == rows


def test_a_view_moves_its_selected_rows_and_says_where_they_went():
    global _qapplication
    if QtWidgets.QApplication.instance() is None:
        # Held for the life of the process: a QApplication that is garbage
        # collected takes every widget built under it down with it.
        _qapplication = QtWidgets.QApplication([])
    model = QtGui.QStandardItemModel()
    for name in 'ABCDE':
        model.appendRow(QtGui.QStandardItem(name))
    view = TreeView()
    view.setModel(model)
    for row in (1, 3):
        view.selectionModel().select(
            model.index(row, 0), QtCore.QItemSelectionModel.SelectionFlag.Select
        )
    orders = []
    view.rowsReordered.connect(orders.append)

    view.move_selected_rows('top')

    assert [model.item(row).text() for row in range(5)] == list('BDACE')
    selected = {index.row() for index in view.selectionModel().selectedIndexes()}
    assert selected == {0, 1}
    assert orders == [[2, 0, 3, 1, 4]]
