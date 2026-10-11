#####################################################################
#                                                                   #
# /tests/test_versions.py                                           #
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
"""Reading the version of an installed module, or why there is none to read."""
from labscript_utils.versions import NoVersionInfo, NotFound, get_version


def test_get_version_reports_a_version_or_why_there_is_none(tmp_path):
    package = tmp_path / 'unversioned'
    package.mkdir()
    (package / '__init__.py').touch()
    assert get_version('unversioned', import_path=str(tmp_path)) is NoVersionInfo
    assert get_version('plsgtbg') is NotFound
    assert isinstance(get_version('labscript_utils'), str)
    assert isinstance(get_version('numpy'), str)
