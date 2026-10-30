#####################################################################
#                                                                   #
# /tests/test_h5_lock.py                                            #
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
"""Deleting a shot file under its zlock."""
import threading

import labscript_utils.h5_lock
import h5py
import pytest

from labscript_utils.h5_lock import delete_shot_file


def test_delete_waits_for_a_reader_then_raises_once_gone(tmp_path):
    path = tmp_path / 'shot.h5'
    with h5py.File(path, 'w'):
        pass
    deleted = threading.Event()

    def delete():
        delete_shot_file(path)
        deleted.set()

    with h5py.File(path, 'r'):
        thread = threading.Thread(target=delete, daemon=True)
        thread.start()
        assert not deleted.wait(0.5)
        assert path.exists()
    thread.join(10)
    assert deleted.is_set()
    assert not path.exists()
    with pytest.raises(OSError):
        delete_shot_file(path)
