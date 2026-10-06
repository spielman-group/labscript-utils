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
"""Opening a file in the labconfig's text editor."""
from types import SimpleNamespace

import labscript_utils.text_editor as text_editor
from labscript_utils.labconfig import LabConfig


def test_a_file_opens_in_the_labconfig_text_editor(monkeypatch, tmp_path):
    # Launching a real editor is the one thing a test cannot do.
    launched = []
    monkeypatch.setattr(
        text_editor, 'subprocess', SimpleNamespace(Popen=launched.append)
    )
    labconfig = tmp_path / 'labconfig.toml'
    monkeypatch.setattr(
        text_editor, 'LabConfig', lambda: LabConfig(config_path=labconfig)
    )
    for arguments in ['-a TextEdit {file}', '--wait']:
        labconfig.write_text(
            "[programs]\ntext_editor = 'open'\n"
            f"text_editor_arguments = '{arguments}'\n"
        )
        text_editor.open_in_editor('/lab/shot.py')
    assert launched == [
        ['open', '-a', 'TextEdit', '/lab/shot.py'],
        ['open', '/lab/shot.py', '--wait'],
    ]
