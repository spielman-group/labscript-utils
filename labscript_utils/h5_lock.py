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
        msg += "------------\n%s------------" % tb
        raise ImportError(msg)
    else:
        raise ImportError('h5_lock must be imported prior to importing h5py')
        
import h5py

_File = h5py.File
class File(_File):
    def __init__(self, name, mode=None, driver=None, libver=None, **kwds):
        if not isinstance(name, h5py._objects.ObjectID):
            kwargs = {}
            if mode == 'r':
                kwargs['read_only'] = True
            # Do not terminate upon SIGTERM while the file is open:
            self.kill_lock = kill_lock
            self.kill_lock.acquire()
            # Ask other zlock users not to open the file while we have it open:
            self.zlock = Lock(path_to_agnostic(name), **kwargs)
            self.zlock.acquire()
        try:
            _File.__init__(self, name, mode, driver, libver, **kwds)
        except:
            if hasattr(self, 'zlock'):
                self.zlock.release()
            if hasattr(self, 'kill_lock'):
                self.kill_lock.release()
            raise

    def close(self):
        _File.close(self)
        if hasattr(self, 'zlock'):
            self.zlock.release()
        if hasattr(self, 'kill_lock'):
            self.kill_lock.release()

    # Not holding h5py's library-wide lock ("phil") in __exit__ avoids a deadlock:
    # close() would take kill_lock._lock under phil, while a garbage collection in a
    # thread holding kill_lock._lock waits for phil to deallocate HDF5 objects.
    def __exit__(self, *args):
        self.close()


def hack_locks_onto_h5py():
    # Monkeypatch h5py so all files are locked:
    h5py.File = File

if os.environ.get('READTHEDOCS'):
    # prevent starting a zlock server on RTD, which always fails
    pass
else:
    connect_to_zlock_server()
    hack_locks_onto_h5py()
