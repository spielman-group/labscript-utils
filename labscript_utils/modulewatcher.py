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


class ModuleWatcher(object):
    """A watcher that reloads modules that have been modified on disk
    
    Only reloads modules imported after instantiation. Does not reload C extensions.

    Args:
        debug (bool, optional): When :code:`True`, prints debugging information
            when reloading modules.
    """
    def __init__(self, debug=False):
        self.debug = debug
        # A lock to hold whenever you don't want modules unloaded:
        self.lock = threading.Lock()

        # The whitelist is the list of names of currently loaded modules:
        self.whitelist = set(sys.modules)
        self.meta_whitelist = list(sys.meta_path)
        self.modified_times = {}
        self.main = threading.Thread(target=self.mainloop)
        self.main.daemon = True
        self.main.start()

    def mainloop(self):
        while True:
            time.sleep(1)
            with self.lock:
                if self.check():
                    self.unload()

    def check(self):
        unload_required = False
        # Look through currently loaded modules:
        for name, module in sys.modules.copy().items():
            # Look only at the modules not in the the whitelist:
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
                    # Whitelist modules in package install directories:
                    self.whitelist.add(name)
                    continue
                # Check and store the modified time of the .py file:
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
                        '%s modified: all non-whitelisted modules ' % module_file
                        + 'will be reloaded next run.\n'
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
