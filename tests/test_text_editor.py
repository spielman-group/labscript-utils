#####################################################################
#                                                                   #
# /tests/test_text_editor.py                                        #
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
"""Opening a file in a program the labconfig names."""
import sys
from types import SimpleNamespace

import pytest

import labscript_utils.programs as programs
import labscript_utils.text_editor as text_editor
from labscript_utils.labconfig import LabConfig


@pytest.mark.skipif(sys.platform == 'win32', reason='Windows opens with os.startfile')
def test_a_file_opens_in_the_program_the_labconfig_names(monkeypatch, tmp_path):
    # Launching a real program is the one thing a test cannot do.
    launched = []
    monkeypatch.setattr(
        programs,
        'subprocess',
        SimpleNamespace(Popen=lambda args, **kwargs: launched.append(args)),
    )
    # A failure would otherwise wait on a modal dialog:
    monkeypatch.setattr(
        text_editor.QtWidgets.QMessageBox, 'warning', lambda *args: pytest.fail(args[2])
    )
    labconfig = tmp_path / 'labconfig.toml'
    monkeypatch.setattr(
        text_editor, 'LabConfig', lambda: LabConfig(config_path=labconfig)
    )
    editors = [('open', '-a TextEdit {file}'), ('open', '--wait'), ('', '')]
    for editor, arguments in editors:
        labconfig.write_text(
            f"[programs]\ntext_editor = '{editor}'\n"
            f"text_editor_arguments = '{arguments}'\n"
        )
        text_editor.open_in_editor('/lab/shot.py')
    labconfig.write_text(
        "[programs]\nhdf5_viewer = 'hdfview'\nhdf5_viewer_arguments = ''\n"
    )
    text_editor.open_in_editor('/lab/shot.h5', program='hdf5_viewer')
    default = ['open', '-t'] if sys.platform == 'darwin' else ['xdg-open']
    assert launched == [
        ['open', '-a', 'TextEdit', '/lab/shot.py'],
        ['open', '/lab/shot.py', '--wait'],
        [*default, '/lab/shot.py'],
        ['hdfview', '/lab/shot.h5'],
    ]
