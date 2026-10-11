#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/shotqueue.py                           #
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
import os

from qtutils.qt import QtCore, QtGui, QtWidgets
from qtutils.qt.QtCore import pyqtSignal as Signal


# An identity the caller attaches to a row. Rows are reported by identity, not
# position: the queue moves on its own, and a position goes stale.
ROW_ID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
# Whether a rule is drawn under a row, to set it apart from those below it.
RULE_BELOW_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2

__all__ = [
    'ROW_ID_ROLE',
    'RULE_BELOW_ROLE',
    'ShotQueueTreeView',
    'ShotQueueWidget',
]


class _RuleBelowDelegate(QtWidgets.QStyledItemDelegate):
    """Draws a rule under any row whose items ask for one."""

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if not index.data(RULE_BELOW_ROLE):
            return
        # Dimmed text colour, not a frame role such as Dark or Mid: those are relative
        # to Window, and in a dark theme Dark sits below Base and the rule cannot be seen.
        colour = QtGui.QColor(option.palette.color(QtGui.QPalette.ColorRole.Text))
        colour.setAlpha(140)
        painter.save()
        painter.setPen(colour)
        painter.drawLine(
            option.rect.left(),
            option.rect.bottom(),
            option.rect.right(),
            option.rect.bottom(),
        )
        painter.restore()


class ShotQueueTreeView(QtWidgets.QTreeView):
    """A tree view of the queue's rows, which asks for their deletion.

    Attributes
    ----------
    deleteRequested : Signal()
        Emitted when Delete or Backspace is pressed.
    """

    deleteRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.header().setStretchLastSection(True)
        self.setAutoScroll(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            event.accept()
            self.deleteRequested.emit()
            return
        super().keyPressEvent(event)


class ShotQueueWidget(QtWidgets.QWidget):
    """A queue of shot files, shown as rows of a tree view.

    ``set_row_infos`` fills it. Rows are reported by the identity the caller gave
    each, not by position.

    Parameters
    ----------
    parent : QWidget, optional
    column_titles : sequence of str
        The title of each column.
    path_column : int
        The column that shows the shot file. It takes the width the others leave,
        which fit their contents.

    Attributes
    ----------
    queue_model : QStandardItemModel
    queue_view : ShotQueueTreeView
    """

    def __init__(self, parent=None, *, column_titles, path_column):
        super().__init__(parent)
        self.column_titles = list(column_titles)
        self.path_column = int(path_column)

        self.queue_model = QtGui.QStandardItemModel(self)
        self.queue_model.setColumnCount(len(self.column_titles))
        for column, title in enumerate(self.column_titles):
            self.queue_model.setHorizontalHeaderItem(column, QtGui.QStandardItem(title))

        self.queue_view = ShotQueueTreeView(self)
        self.queue_view.setModel(self.queue_model)
        self.queue_view.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.queue_view.header().setStretchLastSection(False)
        for column in range(len(self.column_titles)):
            resize_mode = (
                QtWidgets.QHeaderView.ResizeMode.Stretch
                if column == self.path_column
                else QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )
            self.queue_view.header().setSectionResizeMode(column, resize_mode)
        self._rule_delegate = _RuleBelowDelegate(self.queue_view)
        self.queue_view.setItemDelegate(self._rule_delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.queue_view)

    def selected_ids(self):
        """Return the identities of the selected rows, skipping rows given none."""
        ids = []
        for row in self.selected_rows():
            row_id = self.queue_model.item(row, self.path_column).data(ROW_ID_ROLE)
            if row_id is not None:
                ids.append(row_id)
        return ids

    def selected_rows(self):
        """Return the numbers of the selected rows, in ascending order."""
        return sorted(index.row() for index in self.queue_view.selectionModel().selectedRows())

    def select_ids(self, row_ids):
        """Select the rows carrying these identities, ignoring any no row carries.

        The new selection replaces the old one.
        """
        wanted = set(row_ids)
        rows = []
        for row in range(self.queue_model.rowCount()):
            row_id = self.queue_model.item(row, self.path_column).data(ROW_ID_ROLE)
            if row_id is not None and row_id in wanted:
                rows.append(row)
        self._select_rows(rows)

    def set_row_infos(self, row_infos):
        """Replace the rows of the queue.

        Parameters
        ----------
        row_infos : iterable of dict
            One dict per row, in order. Only ``path`` is required.

            path
                The shot file's path, made absolute.
            label
                The text shown in the path column. The file's name by default.
            tooltip
                The tooltip of the path column. The absolute path by default.
            row_id
                The row's identity, as ``selected_ids`` and ``select_ids`` use it.
            columns
                One dict for each column other than the path column, in order,
                with ``text``, ``tooltip`` and ``alignment`` (left and vertically
                centred by default). A column left out is blank.
            background, foreground
                A brush or colour, as ``QStandardItem.setBackground`` and
                ``setForeground`` take, applied to every cell of the row.
            strikeout
                Whether to strike the row through. Default False.
            selectable
                Whether the row can be selected. Default True.
            rule_below
                Whether to draw a rule under the row. Default False.
        """
        self.queue_model.removeRows(0, self.queue_model.rowCount())
        if not row_infos:
            return
        for row_info in row_infos:
            self.queue_model.appendRow(self._create_row_from_info(row_info))

    def _create_row_from_info(self, row_info):
        path = os.path.abspath(str(row_info['path']))
        label = row_info.get('label', os.path.basename(path))
        tooltip = row_info.get('tooltip', path)
        background = row_info.get('background')
        foreground = row_info.get('foreground')
        row_id = row_info.get('row_id')
        # A row that is finished with but cannot be removed, since something else
        # may still hold its file, is struck through.
        strikeout = bool(row_info.get('strikeout', False))
        selectable = row_info.get('selectable', True)
        rule_below = bool(row_info.get('rule_below', False))
        columns = list(row_info.get('columns', []))
        row_items = self._create_padding_items(self.queue_model.columnCount())
        row_items[self.path_column] = self._create_display_item(label, tooltip=tooltip)
        extra_columns = [i for i in range(self.queue_model.columnCount()) if i != self.path_column]
        for column_index, column_info in zip(extra_columns, columns):
            row_items[column_index] = self._create_display_item_from_info(column_info)
        # Both colours go on every cell, since a background alone leaves the
        # theme's text colour, which may be unreadable on it.
        for item in row_items:
            if background is not None:
                item.setBackground(background)
            if foreground is not None:
                item.setForeground(foreground)
            if strikeout:
                font = item.font()
                font.setStrikeOut(True)
                item.setFont(font)
            item.setSelectable(bool(selectable))
            if rule_below:
                item.setData(True, RULE_BELOW_ROLE)
        if row_id is not None:
            row_items[self.path_column].setData(row_id, ROW_ID_ROLE)
        return row_items

    def _create_padding_items(self, count):
        items = []
        for _ in range(max(0, count)):
            items.append(self._create_display_item(''))
        return items

    def _create_display_item(self, text, tooltip='', alignment=None):
        item = QtGui.QStandardItem(str(text))
        item.setEditable(False)
        item.setToolTip(tooltip)
        if alignment is not None:
            item.setTextAlignment(alignment)
        return item

    def _create_display_item_from_info(self, column_info):
        text = column_info.get('text', '')
        tooltip = column_info.get('tooltip', '')
        alignment = column_info.get(
            'alignment',
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
        )
        return self._create_display_item(text, tooltip=tooltip, alignment=alignment)

    def _select_rows(self, rows):
        rows = list(rows)
        selection_model = self.queue_view.selectionModel()
        selection_model.clearSelection()
        for row in rows:
            index = self.queue_model.index(row, self.path_column)
            selection_model.select(
                index,
                QtCore.QItemSelectionModel.SelectionFlag.Select
                | QtCore.QItemSelectionModel.SelectionFlag.Rows,
            )
        if rows:
            self.queue_view.setCurrentIndex(self.queue_model.index(rows[0], self.path_column))
