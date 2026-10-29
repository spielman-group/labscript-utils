#####################################################################
#                                                                   #
# /labscript_utils/text_editor.py                                   #
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
"""Open a file in a program the labconfig names, by default its text editor."""
import os

from qtutils.qt import QtWidgets

from labscript_utils.labconfig import LabConfig
from labscript_utils.programs import open_file


def open_in_editor(path, parent=None, program='text_editor'):
    """Open ``path`` in a program the labconfig names, without waiting for it.

    It is opened by :func:`labscript_utils.programs.open_file`, so an empty program
    opens the operating system's default one. An empty ``path`` opens nothing. When
    the program cannot be launched, a dialog on ``parent`` says so instead, and
    nothing is raised.
    """
    path = os.fspath(path)
    if not path:
        return
    config = LabConfig()
    try:
        open_file(path, program, config)
    except Exception as e:
        QtWidgets.QMessageBox.warning(
            parent,
            'Open file',
            f'Could not open {path}. The {program} is set in the [programs] '
            f'section of {config.config_path}. The error was: {e}',
        )
