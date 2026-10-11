#####################################################################
#                                                                   #
# double_import_denier.py                                           #
#                                                                   #
# Copyright 2018, Chris Billington                                  #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import sys
import os
import traceback
import re
import importlib.util

DEBUG = False
# Tensorflow contains true double imports. This is arguably a bug in tensorflow,
# (reported here: https://github.com/tensorflow/tensorflow/issues/35369), but let's work
# around it since tensorflow is not our problem:
WHITELIST = ['tensorflow', 'tensorflow_core']


class DoubleImportDenier:
    """A module finder that tracks what has been imported and raises an exception
    if the same file is imported under a different name."""

    def __init__(self):
        self.enabled = False
        self.names_by_filepath = {}
        self.tracebacks = {}
        UNKNOWN = ('<unknown: imported prior to double_import_denier.enable()>\n')
        for name, module in list(sys.modules.items()):
            if getattr(module, '__file__', None) is not None:
                path = os.path.realpath(module.__file__)
                if os.path.splitext(os.path.basename(path))[0] == '__init__':
                    # Import path for __init__.py is actually the folder they're in, so
                    # use that instead
                    path = os.path.dirname(path)
                self.names_by_filepath[path] = name
                self.tracebacks[path] = [UNKNOWN, '']

        self.stack = set()

    def find_spec(self, fullname, path=None, target=None):
        # Prevent recursion. If importlib.util.find_spec was called by us and is looking
        # through sys.meta_path for finders, return None so it moves on to the other
        # loaders.
        dict_key = (fullname, tuple(path) if path is not None else None)
        if dict_key in self.stack:
            return
        self.stack.add(dict_key)
        try:
            spec = importlib.util.find_spec(fullname, path)
        except Exception as e:
            if DEBUG:
                print('Exception in importlib.util.find_spec ' + str(e))
            return
        finally:
            self.stack.remove(dict_key)

        if spec is not None and spec.origin is not None and spec.origin != "built-in":
            path = os.path.realpath(spec.origin)
            if DEBUG:
                print('loading', fullname, 'from', path)
            tb = traceback.format_stack()
            other_name = self.names_by_filepath.get(path, None)
            if fullname.split('.', 1)[0] not in WHITELIST:
                if other_name is not None and other_name != fullname:
                    other_tb = self.tracebacks[path]
                    self._raise_error(path, fullname, tb, other_name, other_tb)
            self.names_by_filepath[path] = fullname
            self.tracebacks[path] = tb
        return spec

    def _format_tb(self, tb):
        """Join a stack list, leaving out its last frame and import-machinery frames."""
        frames = [frame for frame in tb[:-1]
                  if 'importlib._bootstrap' not in frame
                  and 'imp.load_module' not in frame
                  and not ('imp.py' in frame
                           and ('load_module' in frame
                                or 'load_source' in frame
                                or 'load_package' in frame))]
        return ''.join(frames)

    def _restore_tracebacklimit_after_exception(self):
        orig_excepthook = sys.excepthook
        exists = hasattr(sys, 'tracebacklimit')
        orig_tracebacklimit = getattr(sys, 'tracebacklimit', None)

        def excepthook(*args, **kwargs):
            orig_excepthook(*args, **kwargs)
            if exists:
                sys.tracebacklimit = orig_tracebacklimit
            else:
                del sys.tracebacklimit
            sys.excepthook = orig_excepthook
        sys.excepthook = excepthook

    def _raise_error(self, path, name, tb, other_name, other_tb):
        msg = """Double import! The same file has been imported under two
        different names, resulting in two copies of the module. This is almost
        certainly a mistake. If you are running a script from within a package
        and want to import another submodule of that package, import it by its
        full path: 'import module.submodule' instead of just 'import
        submodule.'"""

        msg = re.sub(' +',' ', ' '.join(msg.splitlines()))

        tb = self._format_tb(tb)
        other_tb = self._format_tb(other_tb)
        msg += f"\n\nPath imported: {path}\n\n"
        msg += f"Traceback (first time imported, as {other_name}):\n"
        msg += f"------------\n{other_tb}------------\n\n"
        msg += f"Traceback (second time imported, as {name}):\n"
        msg += f"------------\n{tb}------------"

        # Limit the traceback, hiding import-machinery frames. A finally: block cannot
        # restore the limit, as it runs before the exception is printed, so a
        # temporary excepthook does.
        self._restore_tracebacklimit_after_exception()

        sys.tracebacklimit = 2
        raise RuntimeError(msg) from None


_denier = None


def enable():
    """Install the double import denier in ``sys.meta_path``.

    Does nothing if ``--allow-double-imports`` is in ``sys.argv``.

    Raises
    ------
    RuntimeError
        If the denier is already enabled.
    """
    if '--allow-double-imports' in sys.argv:
        # Calls to enable the double import denier are ignored if this command
        # line argument is present.
        return
    global _denier
    if _denier is None:
        _denier = DoubleImportDenier()
    if _denier.enabled:
        raise RuntimeError('already enabled')
    # Compare by class name, so an instance of another copy of the class is caught too.
    for importer in sys.meta_path:
        if importer.__class__.__name__ == DoubleImportDenier.__name__:
            msg = 'Two DoubleImportDenier instances in sys.meta_path!'
            raise AssertionError(msg)
    sys.meta_path.insert(0, _denier)
    _denier.enabled = True
