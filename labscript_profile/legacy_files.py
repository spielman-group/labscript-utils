#####################################################################
#                                                                   #
# /labscript_profile/legacy_files.py                                #
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
"""The warning that a file is read through a legacy form.

It is here, importing only the standard library, so that the profile's bootstrap
can warn without importing labscript_utils; labscript_utils.file_utils exports it.
"""
import os
import threading
import warnings

_legacy_files = set()
_legacy_files_lock = threading.Lock()


def warn_legacy_file(path, legacy):
    """Warn that a file is read through a legacy form, once per file.

    Reading the legacy form will be removed, so the file may not be readable in
    future. The warning is a ``FutureWarning``, given once in a process for each
    file whatever the warning filters say, and names the first legacy form found
    in it.

    Parameters
    ----------
    path : str or path-like
        The file.
    legacy : str
        What the file does in the legacy form, naming the current one, such as
        ``"connects its DDSs as 'channel n', not 'dds n'"``.
    """
    key = os.path.normcase(os.path.abspath(path))
    with _legacy_files_lock:
        if key in _legacy_files:
            return
        _legacy_files.add(key)
    warnings.warn(
        f'{path} {legacy}. Reading that legacy form will be removed, so the file '
        'may not be readable in future.',
        FutureWarning,
        stacklevel=2,
    )
