#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/file_dialogs.py                        #
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
"""File and folder dialogs that return an absolute path, or None if the user cancels.

Each takes the dialog's ``parent`` widget, its ``caption``, the ``directory`` (folder
or file) it starts at and, except ``choose_folder``, a ``name_filter`` such as
``"HDF5 files (*.h5)"``. The macOS save panel may add an extension of its own to a
name that has none, so give ``save_file`` a file name, not only a folder.
"""
import os

from qtutils.qt import QtWidgets

QFileDialog = QtWidgets.QFileDialog


def open_file(parent, caption, directory, name_filter):
    """Ask for one existing file."""
    path, _ = QFileDialog.getOpenFileName(parent, caption, directory, name_filter)
    return os.path.abspath(path) if path else None


def open_files(parent, caption, directory, name_filter):
    """Ask for any number of existing files, returning a list of paths."""
    paths, _ = QFileDialog.getOpenFileNames(parent, caption, directory, name_filter)
    return [os.path.abspath(path) for path in paths] or None


def save_file(parent, caption, directory, name_filter):
    """Ask for the name of a file to save to."""
    path, _ = QFileDialog.getSaveFileName(parent, caption, directory, name_filter)
    return os.path.abspath(path) if path else None


def choose_folder(parent, caption, directory):
    """Ask for an existing folder."""
    path = QFileDialog.getExistingDirectory(parent, caption, directory)
    return os.path.abspath(path) if path else None
