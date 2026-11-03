#####################################################################
#                                                                   #
# /tests/test_shotqueue.py                                          #
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
"""Selection and visual row markers in the shared shot queue."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qtutils.qt.QtCore import Qt
from qtutils.qt.QtGui import QColor, QPalette
from qtutils.qt.QtWidgets import QApplication

from labscript_utils.qtwidgets.shotqueue import ShotQueueWidget


_qapplication = None


def make_widget():
    global _qapplication
    if QApplication.instance() is None:
        # Held for the life of the process: a QApplication that is garbage
        # collected takes every widget built under it down with it.
        _qapplication = QApplication([])
    return ShotQueueWidget(column_titles=['Mode', 'Shot file'], path_column=1)


def row_backgrounds(widget, row):
    model = widget.queue_model
    return [
        model.item(row, column).data(Qt.BackgroundRole)
        for column in range(model.columnCount())
    ]


def test_selecting_several_rows_by_identity_keeps_them_all_selected():
    widget = make_widget()
    widget.set_row_infos([{'path': f'/tmp/shot_{i}.h5', 'row_id': i} for i in range(5)])
    widget.select_ids([1, 3, 4])
    assert widget.selected_ids() == [1, 3, 4]


def test_row_background_colours_every_column_of_that_row():
    widget = make_widget()
    widget.set_row_infos(
        [
            {'path': '/tmp/shot_a.h5', 'background': QColor('#ccffcc')},
            {'path': '/tmp/shot_b.h5'},
        ]
    )
    coloured = row_backgrounds(widget, 0)
    assert all(brush is not None for brush in coloured)
    assert all(brush.color() == QColor('#ccffcc') for brush in coloured)
    assert all(brush is None for brush in row_backgrounds(widget, 1))


def row_fonts(widget, row):
    return [
        widget.queue_model.item(row, column).font()
        for column in range(widget.queue_model.columnCount())
    ]


def test_a_struck_out_row_is_struck_out_in_every_column():
    # Struck-through rows are finished with but may still have their files in use.
    widget = make_widget()
    widget.set_row_infos(
        [
            {'path': '/tmp/shot_a.h5', 'strikeout': True},
            {'path': '/tmp/shot_b.h5'},
        ]
    )
    assert all(font.strikeOut() for font in row_fonts(widget, 0))
    assert not any(font.strikeOut() for font in row_fonts(widget, 1))


def luminance(colour):
    return (
        0.2126 * colour.redF() + 0.7152 * colour.greenF() + 0.0722 * colour.blueF()
    )


DARK_THEME = {
    QPalette.ColorRole.Base: '#232323',
    QPalette.ColorRole.Text: '#dddddd',
    QPalette.ColorRole.Window: '#2b2b2b',
    QPalette.ColorRole.WindowText: '#dddddd',
    # Below Base, which is where a dark theme puts it and the whole point of
    # this test: a rule drawn in Dark is then invisible on the list.
    QPalette.ColorRole.Dark: '#191919',
    QPalette.ColorRole.Mid: '#3a3a3a',
    QPalette.ColorRole.Shadow: '#000000',
}


def test_the_rule_under_a_row_is_visible_on_a_dark_theme():
    # Dark is relative to Window and can be indistinguishable from the list's Base.
    widget = make_widget()
    application = QApplication.instance()
    saved = application.palette()
    palette = QPalette(saved)
    for role, value in DARK_THEME.items():
        palette.setColor(role, QColor(value))
    application.setPalette(palette)
    try:
        widget.set_row_infos(
            [
                {'path': '/tmp/shot_a.h5', 'rule_below': True},
                {'path': '/tmp/shot_b.h5'},
            ]
        )
        widget.resize(400, 80)
        widget.show()
        application.processEvents()

        view = widget.queue_view
        image = view.viewport().grab().toImage()
        # grab() returns device pixels; visualRect returns logical coordinates.
        # Scale the sample positions so they follow the rule on HiDPI displays.
        scale = image.devicePixelRatio() or 1
        first = view.visualRect(widget.queue_model.index(0, widget.path_column))
        second = view.visualRect(widget.queue_model.index(1, widget.path_column))
        x = int(first.center().x() * scale)
        background = QColor(image.pixel(x, int(second.center().y() * scale)))
        contrast = max(
            abs(luminance(QColor(image.pixel(x, int(y * scale)))) - luminance(background))
            for y in range(first.bottom() - 1, first.bottom() + 2)
        )
    finally:
        application.setPalette(saved)

    assert contrast > 0.15, (
        'the rule is %.3f in luminance from the rows it separates, which is '
        'not a line anybody can see' % contrast
    )
