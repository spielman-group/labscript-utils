#####################################################################
#                                                                   #
# shared_drive.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
r"""Convert paths between this computer's shared drive and a form valid anywhere.

The labconfig's ``[paths] shared_drive`` is where this computer mounts the shared
drive. ``prefix`` is that path, ending in a path separator. In the form that is
valid on any computer a path on the shared drive is ``Z:\`` followed by its
backslash-separated path relative to the drive.
"""
import os

from labscript_utils.labconfig import LabConfig

_config = LabConfig(required_params={'paths': ['shared_drive']})
prefix = _config.get('paths', 'shared_drive')

# path_to_agnostic matches the prefix as text, so ending it at a separator stops a
# folder that merely starts with the same name from matching:
if not prefix.endswith(os.path.sep):
    prefix += os.path.sep


def path_to_agnostic(path):
    """Return ``path`` in the form that is valid on any computer.

    A path on the shared drive is written ``Z:\\<path relative to the drive>``, with
    backslashes; any other is made absolute.
    """
    path = os.path.abspath(path)
    if path.startswith(prefix):
        path = path.split(prefix, 1)[1]
        path = 'Z:\\' + path
        path = path.replace(os.path.sep, '\\')
    return path


def path_to_local(path):
    """Return the path on this computer for a path in the form valid on any computer.

    A path starting with ``Z:\\`` is placed on this computer's shared drive; any
    other is returned unchanged.
    """
    if path.startswith('Z:\\'):
        path = path.split('Z:\\', 1)[1]
        path = path.replace('\\', os.path.sep)
        path = os.path.join(prefix, path)
    return path
