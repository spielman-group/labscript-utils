#####################################################################
#                                                                   #
# modulewatcher.py                                                  #
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
import threading
import time
import os
import site
import sysconfig


# Directories in which the standard library and installed packages may be located.
# Modules in these locations will be whitelisted:
PKGDIRS = [
    sysconfig.get_path('platstdlib'),
    sysconfig.get_path('platlib'),
    sysconfig.get_path('stdlib'),
    sysconfig.get_path('purelib'),
    site.getusersitepackages(),
]
PKGDIRS += site.getsitepackages()
PKGDIRS = set(PKGDIRS)


class ModuleWatcher:
    """Unload modules that have been modified on disk, so that they are
    reloaded at their next import.

    Only modules imported after instantiation are watched, and only ``.py``
    modules outside the standard library and installed packages. When one of
    them is modified, all of the watched modules are unloaded. C extensions are
    not reloaded. A background thread checks once a second.

    Parameters
    ----------
    debug : bool, optional
        Print the whitelist and the unloaded modules each time modules are
        unloaded.

    Attributes
    ----------
    lock : threading.Lock
        Held while modules are checked and unloaded. Hold it to stop modules
        being unloaded while they are in use.
    """
    def __init__(self, debug=False):
        self.debug = debug
        # A lock to hold whenever you don't want modules unloaded:
        self.lock = threading.Lock()

        # The whitelist is the list of names of currently loaded modules:
        self.whitelist = set(sys.modules)
        self.meta_whitelist = list(sys.meta_path)
        self.modified_times = {}
        self.main = threading.Thread(target=self.mainloop, daemon=True)
        self.main.start()

    def mainloop(self):
        while True:
            time.sleep(1)
            with self.lock:
                if self.check():
                    self.unload()

    def check(self):
        unload_required = False
        for name, module in sys.modules.copy().items():
            if name not in self.whitelist:
                # Only consider modules with a non-None __file__ that are .py or .pyc
                # files on disk, outside the package directories. Others are
                # whitelisted so later calls skip them.
                if getattr(module, '__file__', None) is None:
                    self.whitelist.add(name)
                    continue
                module_file = module.__file__
                if module_file.endswith('.pyc'):
                    module_file = os.path.splitext(module_file)[0] + '.py'
                if not module_file.endswith('.py') or not os.path.exists(module_file):
                    self.whitelist.add(name)
                    continue
                if any(module_file.startswith(s + os.path.sep) for s in PKGDIRS):
                    self.whitelist.add(name)
                    continue
                modified_time = os.path.getmtime(module_file)
                previous_modified_time = self.modified_times.setdefault(
                    name, modified_time
                )
                self.modified_times[name] = modified_time
                if modified_time != previous_modified_time:
                    # A module has been modified! Unload all modules not in the
                    # whitelist:
                    unload_required = True
                    message = (
                        f'{module_file} modified: all non-whitelisted modules '
                        'will be reloaded next run.\n'
                    )
                    sys.stderr.write(message)
        return unload_required

    def unload(self):
        if self.debug:
            print("ModuleWatcher: whitelist is:")
            for name in sorted(self.whitelist):
                print("    " + name)
            print("\nModuleWatcher: modules unloaded:")
        for name in sorted(sys.modules):
            if name not in self.whitelist:
                # Unload rather than reload: the caveats about existing references are
                # the same, but an exception in the import surfaces when the module is
                # next imported, not here.
                del sys.modules[name]
                if name in self.modified_times:
                    del self.modified_times[name]
                if self.debug:
                    print("    " + name)
        # Restore sys.meta_path in place, keeping its order, as other code may hold it.
        sys.meta_path[:] = self.meta_whitelist
