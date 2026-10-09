#####################################################################
#                                                                   #
# shotqueue.py                                                      #
#                                                                   #
# Copyright 2026, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import os

from qtutils.qt.QtCore import *
from qtutils.qt.QtGui import *
from qtutils.qt.QtWidgets import *
from qtutils.qt.QtCore import pyqtSignal as Signal


FILEPATH_COLUMN = 0
# An identity the caller attaches to a row, and gets back when asked what is
# selected. Rows are reported by identity rather than by position because the
# queue behind the widget moves on its own -- a shot finishing removes a row
# while the operator has one selected -- and a position that meant one row when
# it was drawn means another by the time it is acted on.
ROW_ID_ROLE = Qt.UserRole + 1
# Whether a rule is drawn under a row, to set it apart from those below it.
RULE_BELOW_ROLE = Qt.UserRole + 2
__all__ = [
    'FILEPATH_COLUMN',
    'ROW_ID_ROLE',
    'RULE_BELOW_ROLE',
    'ShotQueueTreeView',
    'ShotQueueWidget',
]


class _RuleBelowDelegate(QStyledItemDelegate):
    """Draws a rule under any row whose items ask for one."""

    def paint(self, painter, option, index):
        QStyledItemDelegate.paint(self, painter, option, index)
        if not index.data(RULE_BELOW_ROLE):
            return
        # From the text colour, dimmed -- not from a frame role like Dark or
        # Mid. Those are defined relative to Window rather than to the list a
        # row sits on, and a dark theme puts Dark *below* Base: measured
        # against a #232323 list, a Dark rule differs by 0.04 in luminance and
        # cannot be seen at all. Text against Base is the one contrast every
        # usable theme has to get right, whichever way round it is.
        colour = QColor(option.palette.color(QPalette.ColorRole.Text))
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


class ShotQueueTreeView(QTreeView):
    """Generic queue view with delete-key handling."""

    deleteRequested = Signal()

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)
        self.header().setStretchLastSection(True)
        self.setAutoScroll(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            event.accept()
            self.deleteRequested.emit()
            return
        QTreeView.keyPressEvent(self, event)


class ShotQueueWidget(QWidget):
    """Reusable shot queue editor widget."""

    def __init__(self, parent=None, *, column_titles, path_column=FILEPATH_COLUMN):
        QWidget.__init__(self, parent)
        self.column_titles = list(column_titles)
        self.path_column = int(path_column)

        self.queue_model = QStandardItemModel(self)
        self.queue_model.setColumnCount(len(self.column_titles))
        for column, title in enumerate(self.column_titles):
            self.queue_model.setHorizontalHeaderItem(column, QStandardItem(title))

        self.queue_view = ShotQueueTreeView(self)
        self.queue_view.setModel(self.queue_model)
        self.queue_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.queue_view.header().setStretchLastSection(False)
        for column in range(len(self.column_titles)):
            resize_mode = (
                QHeaderView.Stretch
                if column == self.path_column
                else QHeaderView.ResizeToContents
            )
            self.queue_view.header().setSectionResizeMode(column, resize_mode)
        self._rule_delegate = _RuleBelowDelegate(self.queue_view)
        self.queue_view.setItemDelegate(self._rule_delegate)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.queue_view)

        self._update_button_states()

    def selected_ids(self):
        """The identities of the selected rows, skipping rows given none."""
        ids = []
        for row in self.selected_rows():
            row_id = self.queue_model.item(row, self.path_column).data(ROW_ID_ROLE)
            if row_id is not None:
                ids.append(row_id)
        return ids

    def selected_rows(self):
        return sorted(index.row() for index in self.queue_view.selectionModel().selectedRows())

    def select_ids(self, row_ids):
        """Reselect the rows carrying these identities, ignoring any gone."""
        wanted = set(row_ids)
        rows = []
        for row in range(self.queue_model.rowCount()):
            row_id = self.queue_model.item(row, self.path_column).data(ROW_ID_ROLE)
            if row_id is not None and row_id in wanted:
                rows.append(row)
        self._select_rows(rows)

    def set_row_infos(self, row_infos):
        self.queue_model.removeRows(0, self.queue_model.rowCount())
        if not row_infos:
            return
        for row_info in row_infos:
            self.queue_model.appendRow(self._create_row_from_info(row_info))

    def _create_row_from_info(self, row_info):
        path = os.path.abspath(str(row_info['path']))
        label = row_info.get('label', os.path.basename(path))
        tooltip = row_info.get('tooltip', path)
        # Anything QStandardItem.setBackground()/setForeground() accept, or
        # None for the default. What a colour means is the caller's business;
        # the widget only makes sure it marks the whole row and not one cell of
        # it. Both, because a background alone leaves the theme's own text
        # colour on it -- pale text on a pale fill, unreadable, if the two were
        # chosen for different themes:
        background = row_info.get('background')
        foreground = row_info.get('foreground')
        row_id = row_info.get('row_id')
        # A row that is still here but finished with, which the caller cannot
        # simply remove -- something else may still hold its file. Struck
        # through says both halves at once.
        strikeout = bool(row_info.get('strikeout', False))
        selectable = row_info.get('selectable', True)
        rule_below = bool(row_info.get('rule_below', False))
        columns = list(row_info.get('columns', []))
        row_items = self._create_padding_items(self.queue_model.columnCount())
        row_items[self.path_column] = self._create_display_item(label, tooltip=tooltip)
        extra_columns = [i for i in range(self.queue_model.columnCount()) if i != self.path_column]
        for column_index, column_info in zip(extra_columns, columns):
            row_items[column_index] = self._create_display_item_from_info(column_info)
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
        item = QStandardItem(str(text))
        item.setEditable(False)
        item.setToolTip(tooltip)
        if alignment is not None:
            item.setTextAlignment(alignment)
        return item

    def _create_display_item_from_info(self, column_info):
        text = column_info.get('text', '')
        tooltip = column_info.get('tooltip', '')
        alignment = column_info.get('alignment', Qt.AlignLeft | Qt.AlignVCenter)
        return self._create_display_item(text, tooltip=tooltip, alignment=alignment)

    def _update_button_states(self):
        pass

    def _select_rows(self, rows):
        rows = list(rows)
        selection_model = self.queue_view.selectionModel()
        selection_model.clearSelection()
        for row in rows:
            index = self.queue_model.index(row, self.path_column)
            selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        if rows:
            self.queue_view.setCurrentIndex(self.queue_model.index(rows[0], self.path_column))
