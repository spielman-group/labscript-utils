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
"""Open a file in the text editor the labconfig names."""
import os
import subprocess

from qtutils.qt import QtWidgets

from labscript_utils.labconfig import LabConfig


def open_in_editor(path, parent=None):
    """Open ``path`` in the labconfig's text editor, without waiting for it.

    The editor is ``[programs] text_editor``, given ``text_editor_arguments``.
    Each ``{file}`` in the arguments is replaced by ``path``; with none, ``path``
    comes before them. When no editor is set, or it cannot be launched, a dialog
    says so instead, and nothing is raised.

    Parameters
    ----------
    path : str or os.PathLike
        The file to open. An empty path opens nothing.
    parent : QWidget, optional
        The window the dialog belongs to.
    """
    path = os.fspath(path)
    if not path:
        return
    config = LabConfig()
    editor = config.get('programs', 'text_editor', fallback='')
    arguments = config.get('programs', 'text_editor_arguments', fallback='')
    if not editor:
        QtWidgets.QMessageBox.warning(
            parent,
            'Text editor',
            f'No text editor is set under [programs] in {config.config_path}.',
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
        subprocess.Popen([editor, *arguments])
    except Exception as e:
        QtWidgets.QMessageBox.warning(
            parent,
            'Text editor',
            f'Could not launch the text editor set in {config.config_path}: {e}',
        )
