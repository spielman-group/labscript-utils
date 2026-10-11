#####################################################################
#                                                                   #
# impprof.py                                                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import time


class _ProfilingImporter:
    def __init__(self):
        self.enabled = False
        self.normal_import = None
        self.depth = 0
        self.threshold = 0
        try:
            self.builtins_dict = __builtins__.__dict__
        except AttributeError:
            self.builtins_dict = __builtins__

    def profiling_import(self, name, *args, **kwargs):
        self.depth += 1
        start_time = time.time()
        try:
            result = self.normal_import(name, *args, **kwargs)
        finally:
            self.depth -= 1
        time_taken = time.time() - start_time
        if time_taken > self.threshold:
            print(' '*self.depth + f'[{time_taken:.2f}] import {name}')
        return result

    def enable(self, threshold=0.1):
        """Print each import that takes longer than ``threshold`` seconds.

        Parameters
        ----------
        threshold : float, optional
            Time in seconds above which an import is printed. Default 0.1.

        Raises
        ------
        RuntimeError
            If import profiling is already enabled.
        """
        if self.enabled:
            raise RuntimeError('Already enabled')
        self.enabled = True
        self.threshold = threshold
        self.normal_import = __import__
        self.builtins_dict['__import__'] = self.profiling_import

    def disable(self):
        """Stop printing import times.

        Raises
        ------
        RuntimeError
            If import profiling is not enabled.
        """
        if not self.enabled:
            raise RuntimeError('Not enabled')
        self.enabled = False
        self.builtins_dict['__import__'] = self.normal_import
        self.normal_import = None


_profiling_importer = _ProfilingImporter()
enable = _profiling_importer.enable
disable = _profiling_importer.disable
