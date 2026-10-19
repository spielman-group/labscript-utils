#####################################################################
#                                                                   #
# /labscript_utils/file_utils.py                                    #
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

import os
import re
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


def next_available_indexed_filepath(filepath, suffix_format, start=None):
    """Return the first non-existent filepath created by appending a formatted suffix.

    The suffix goes between the filepath's stem and its extension. If filepath
    already ends with a suffix matching ``suffix_format``, that suffix is
    stripped first. Returns the filepath and the index used to build it.

    Parameters
    ----------
    suffix_format : str
        Format string with a single ``index`` field, such as ``'_{index:03d}'``.
    start : int, optional
        First index to try. If ``None``, the search begins one past the index of
        an existing suffix on ``filepath``, or at 0 if it has none.
    """
    basename, ext = os.path.splitext(filepath)
    suffix_pattern = re.escape(suffix_format)
    suffix_pattern = re.sub(
        r'\\\{index(?::[^}]*)?\\\}',
        lambda match: r'(?P<index>\d+)',
        suffix_pattern,
    )
    match = re.search(suffix_pattern + r'$', basename)
    if match is not None:
        basename = basename[:match.start()]
        if start is None:
            start = int(match.group('index')) + 1
    if start is None:
        start = 0
    index = start
    while True:
        candidate = basename + suffix_format.format(index=index) + ext
        if not os.path.exists(candidate):
            return candidate, index
        index += 1
