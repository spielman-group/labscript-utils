#####################################################################
#                                                                   #
# /tests/test_labconfig.py                                          #
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
"""The name of the file save_appconfig writes, for every name it can be given.

A save panel can hand back a name without the extension it was offered, or with
one the host chose, so the name save_appconfig receives is not always the name
asked for.
"""
import os

import pytest

from labscript_utils.labconfig import save_appconfig


@pytest.mark.parametrize(
    'given, written',
    [
        ('test', 'test.toml'),
        ('test.toml', 'test.toml'),
        # An extension that is not an app config's is part of the name:
        ('test.cfg', 'test.cfg.toml'),
        # A legacy INI name is the same configuration, so TOML replaces it:
        ('test.ini', 'test.toml'),
        ('rb.87.imaging', 'rb.87.imaging.toml'),
    ],
)
def test_save_appconfig_names_the_file_it_writes(tmp_path, given, written):
    save_appconfig(tmp_path / given, {'state': {'value': 1}})
    assert os.listdir(tmp_path) == [written]
