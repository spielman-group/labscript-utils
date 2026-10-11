#####################################################################
#                                                                   #
# /docs/make_pyqt6_inventory.py                                     #
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
"""Write ``source/pyqt6-modified-objects.inv``, which links Qt names in the docs.

It holds the classes and enums in Riverbank's PyQt6 ``objects.inv``, each also
under its short names, so that ``QWidget`` and ``QtWidgets.QWidget`` resolve as
``PyQt6.QtWidgets.QWidget`` does. This follows MSLNZ/msl-qt's
``create_pyqt_objects.py`` (MIT License).
"""
import zlib
from pathlib import Path
from urllib.request import urlopen

SOURCE = 'https://www.riverbankcomputing.com/static/Docs/PyQt6/objects.inv'
TARGET = Path(__file__).parent / 'source' / 'pyqt6-modified-objects.inv'

raw = urlopen(SOURCE).read().split(b'\n', 4)
version = raw[2].decode().split(': ', 1)[1]
entries = {}
for line in zlib.decompress(raw[4]).decode().splitlines():
    name, role, _priority, location, _dispname = line.split(' ', 4)
    if role not in ('sip:class', 'sip:enum') or not name.startswith('PyQt6.'):
        continue
    location = location.replace('##', '#')
    qualified = name.removeprefix('PyQt6.')
    short = qualified.split('.', 1)[1] if '.' in qualified else qualified
    for alias in (name, qualified, short):
        entries.setdefault(alias, location)
body = ''.join(f'{alias} py:class 1 {location} -\n' for alias, location in sorted(entries.items()))
header = (
    '# Sphinx inventory version 2\n# Project: PyQt\n'
    f'# Version: {version}\n# The remainder of this file is compressed using zlib.\n'
)
TARGET.write_bytes(header.encode() + zlib.compress(body.encode(), 9))
