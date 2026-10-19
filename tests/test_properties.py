#####################################################################
#                                                                   #
# /tests/test_properties.py                                         #
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
"""Device properties read from a shot file, old ones included."""
import warnings

import h5py
import numpy as np

from labscript_utils import properties
from labscript_utils.file_utils import warn_legacy_file


def test_an_old_file_reads_and_warns_once(tmp_path):
    path = tmp_path / 'old_shot.h5'
    dtype = [('name', 'S16'), ('properties', 'S64'), ('unit conversion params', 'S16')]
    row = (b'device', repr({'answer': 42}).encode(), b'{}')
    with h5py.File(path, 'w') as h5_file:
        h5_file['connection table'] = np.array([row], dtype=dtype)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        with h5py.File(path, 'r') as h5_file:
            for _ in range(2):
                assert properties.get(
                    h5_file, 'device', 'connection_table_properties'
                ) == {'answer': 42}
                assert properties.get(
                    h5_file, 'device', 'unit_conversion_parameters'
                ) == {}
        # The same file, named another way, in another legacy form:
        warn_legacy_file(tmp_path / '.' / 'old_shot.h5', 'is old in another way')

    assert [warning.category for warning in caught] == [FutureWarning]
    assert str(path) in str(caught[0].message)
