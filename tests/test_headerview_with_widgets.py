#####################################################################
#                                                                   #
# /tests/test_headerview_with_widgets.py                            #
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
"""Header widgets staying over their columns as columns are removed."""
from qtutils.qt import QtGui, QtWidgets

from labscript_utils.qtwidgets.headerview_with_widgets import (
    HorizontalHeaderViewWithWidgets,
)


_qapplication = None


def test_removing_columns_keeps_the_rest_and_their_widgets():
    global _qapplication
    if QtWidgets.QApplication.instance() is None:
        # Held for the life of the process: a QApplication that is garbage
        # collected takes every widget built under it down with it.
        _qapplication = QtWidgets.QApplication([])
    model = QtGui.QStandardItemModel()
    view = QtWidgets.QTableView()
    header = HorizontalHeaderViewWithWidgets(model)
    view.setModel(model)
    view.setHorizontalHeader(header)
    model.setHorizontalHeaderLabels([f'col{i}' for i in range(6)])
    model.appendRow([QtGui.QStandardItem(str(i)) for i in range(6)])
    removed, kept = QtWidgets.QCheckBox(), QtWidgets.QCheckBox()
    header.setWidget(2, removed)
    header.setWidget(4, kept)
    view.show()
    QtWidgets.QApplication.processEvents()

    model.removeColumn(2)
    model.removeColumn(0)
    QtWidgets.QApplication.processEvents()

    assert header.count() == model.columnCount() == 4
    assert header.widgets == {2: kept}
    assert removed.parent() is None
    assert kept.x() == header.sectionViewportPosition(2) + 3
