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
import subprocess

from qtutils.qt import QtWidgets

from labscript_utils.labconfig import LabConfig


def open_in_editor(path, parent=None, program='text_editor'):
    """Open ``path`` in a program the labconfig names, without waiting for it.

    The program is ``[programs] <program>``, given ``<program>_arguments``. Each
    ``{file}`` in the arguments is replaced by ``path``; with none, ``path`` comes
    before them. When the program is not set, or cannot be launched, a dialog
    says so instead, and nothing is raised.

    Parameters
    ----------
    path : str or os.PathLike
        The file to open. An empty path opens nothing.
    parent : QWidget, optional
        The window the dialog belongs to.
    program : str, optional
        The ``[programs]`` key naming the program, such as ``'hdf5_viewer'``.
    """
    path = os.fspath(path)
    if not path:
        return
    config = LabConfig()
    executable = config.get('programs', program, fallback='')
    arguments = config.get('programs', f'{program}_arguments', fallback='')
    if not executable:
        QtWidgets.QMessageBox.warning(
            parent,
            'Open file',
            f'No {program} is set under [programs] in {config.config_path}.',
        )
        return
    # A TOML array gives the arguments as a list already.
    if isinstance(arguments, str):
        arguments = arguments.split()
    if any('{file}' in argument for argument in arguments):
        arguments = [argument.replace('{file}', path) for argument in arguments]
    else:
        arguments = [path, *arguments]
    try:
        subprocess.Popen([executable, *arguments])
    except Exception as e:
        QtWidgets.QMessageBox.warning(
            parent,
            'Open file',
            f'Could not launch the {program} set in {config.config_path}: {e}',
        )
