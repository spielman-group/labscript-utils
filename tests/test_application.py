#####################################################################
#                                                                   #
# /tests/test_application.py                                        #
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
"""Application setup and a main window's saved geometry."""
from qtutils.qt import PYQT_LIBS, QT_ENV, QtCore, QtGui, QtWidgets

from labscript_utils.qtwidgets.application import (
    FONT_PIXEL_SIZE, LabscriptGuiApplication, setup_application,
)


_qapplication = None


def make_application():
    global _qapplication
    if QtWidgets.QApplication.instance() is None:
        # Held for the life of the process: a QApplication that is garbage
        # collected takes every widget built under it down with it.
        _qapplication = QtWidgets.QApplication([])
    app = LabscriptGuiApplication()
    app.ui = QtWidgets.QMainWindow()
    return app


def test_a_maximised_window_restores_maximised_and_unmaximises_to_its_saved_size():
    app = make_application()
    app.ui.resize(400, 300)
    app.ui.move(50, 60)
    app.ui.show()
    app.ui.showMaximized()
    QtWidgets.QApplication.processEvents()
    saved = app.geometry_save_data()

    restarted = make_application()
    restarted.restore_geometry(saved)
    restarted.ui.show()
    QtWidgets.QApplication.processEvents()
    assert restarted.ui.isMaximized()
    assert restarted.geometry_save_data() == saved, 'it would creep on each restart'

    restarted.ui.showNormal()
    QtWidgets.QApplication.processEvents()
    assert restarted.ui.size() == QtCore.QSize(400, 300)
    assert restarted.ui.pos() == QtCore.QPoint(50, 60)


def test_a_full_screen_window_saves_the_size_it_returns_to():
    app = make_application()
    app.ui.resize(400, 300)
    app.ui.move(50, 60)
    app.ui.show()
    QtWidgets.QApplication.processEvents()
    normal = app.geometry_save_data()

    app.ui.showFullScreen()
    QtWidgets.QApplication.processEvents()
    full_screen = app.geometry_save_data()

    assert full_screen['window_size'] == normal['window_size'] == (400, 300)
    assert full_screen['window_pos'] == normal['window_pos']


def test_repeated_setup_restyles_without_adding_event_sources():
    make_application()
    app = QtWidgets.QApplication.instance()
    setup_application(app)
    timers = app.findChildren(QtCore.QTimer)
    palette_changed = (
        app.paletteChanged if QT_ENV in PYQT_LIBS
        else QtCore.SIGNAL('paletteChanged(QPalette)')
    )
    connections = app.receivers(palette_changed)
    app.setFont(QtGui.QFont('Ubuntu', 8))
    setup_application(app)
    assert app.findChildren(QtCore.QTimer) == timers
    assert app.receivers(palette_changed) == connections
    assert app.font().pixelSize() == FONT_PIXEL_SIZE
