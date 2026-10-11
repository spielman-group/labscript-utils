#####################################################################
#                                                                   #
# h5_lock.py                                                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Make h5py files lock themselves with zlock while they are open.

Import this module before anything imports h5py: it raises ImportError if h5py
is already imported. Importing it connects to the zlock server, unless the
READTHEDOCS environment variable is set, and replaces ``h5py.File`` with a
subclass that holds a zlock on the file.
"""
import sys
import os

from labscript_utils.ls_zprocess import Lock, connect_to_zlock_server, kill_lock
from labscript_utils import dedent
from labscript_utils.shared_drive import path_to_agnostic

if 'h5py' in sys.modules:
    import labscript_utils.double_import_denier
    import h5py
    denier = labscript_utils.double_import_denier._denier
    if denier is not None and denier.enabled:
        tb = denier._format_tb(denier.tracebacks[os.path.dirname(h5py.__file__)])
        msg = """Error importing h5_lock: h5py has already been imported. h5_lock must
            be imported before any code imports h5py. The above traceback shows where
            h5_lock was imported, and the below traceback shows where h5py was imported
            prior."""
        msg = dedent(msg)
        msg += "\n\nTraceback (h5py import):\n"
        msg += f"------------\n{tb}------------"
        raise ImportError(msg)
    else:
        raise ImportError('h5_lock must be imported prior to importing h5py')

import h5py

_File = h5py.File


class File(_File):
    """An ``h5py.File`` that holds a zlock on its path, and the kill lock, while open.

    The locks are not taken when ``name`` is an h5py object ID rather than a path.
    The zlock is read-only if ``mode`` is 'r'.
    """

    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        try:
            if not isinstance(name, h5py._objects.ObjectID):
                kwargs = {}
                if mode == 'r':
                    kwargs['read_only'] = True
                # Do not terminate upon SIGTERM while the file is open:
                kill_lock.acquire()
                self.kill_lock = kill_lock
                # Ask other zlock users not to open the file while we have it open:
                zlock = Lock(path_to_agnostic(name), **kwargs)
                zlock.acquire()
                self.zlock = zlock
            super().__init__(name, mode, driver, libver, **kwds)
        except:
            if hasattr(self, 'zlock'):
                self.zlock.release()
            if hasattr(self, 'kill_lock'):
                self.kill_lock.release()
            raise

    def close(self):
        super().close()
        if hasattr(self, 'zlock'):
            self.zlock.release()
        if hasattr(self, 'kill_lock'):
            self.kill_lock.release()

    # __exit__ is overridden so as not to hold h5py's library-wide lock ("phil"):
    # close() would take kill_lock._lock under phil, while a garbage collection in a
    # thread holding kill_lock._lock waits for phil to deallocate HDF5 objects.
    def __exit__(self, *args):
        self.close()


def hack_locks_onto_h5py():
    """Replace ``h5py.File`` with the locking :class:`File`."""
    h5py.File = File


if os.environ.get('READTHEDOCS'):
    # prevent starting a zlock server on RTD, which always fails
    pass
else:
    connect_to_zlock_server()
    hack_locks_onto_h5py()
