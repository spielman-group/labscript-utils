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


def next_available_indexed_filepath(filepath, suffix_format, start=None):
    """Return the first non-existent filepath created by appending a formatted suffix.

    The suffix goes between the filepath's stem and its extension. If filepath
    already ends with a suffix matching ``suffix_format``, that suffix is
    stripped first.

    Parameters
    ----------
    filepath : str or path-like
        Path whose stem and extension the suffix is placed between.
    suffix_format : str
        Format string with a single ``index`` field, such as ``'_{index:03d}'``.
    start : int, optional
        First index to try. If ``None``, the search begins one past the index of
        an existing suffix on ``filepath``, or at 0 if it has none.

    Returns
    -------
    candidate : str
        The first filepath that does not exist.
    index : int
        The index used to build ``candidate``.
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
