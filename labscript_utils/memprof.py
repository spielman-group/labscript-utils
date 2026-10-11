#####################################################################
#                                                                   #
# memprof.py                                                        #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import gc


class MemoryProfiler:
    """Count the instances of each type in the interpreter, to detect Python memory
    leaks."""

    def __init__(self):
        self.filepath = None
        self.initial_counts = None

    def count_types(self):
        types = {}
        for obj in gc.get_objects():
            try:
                c = obj.__class__
            except AttributeError:
                c = type(obj)
            try:
                types[c] += 1
            except KeyError:
                types[c] = 1
        self.write_to_file(types)
        return types

    def write_to_file(self, types):
        with open(self.filepath, 'w') as f:
            names = list(types.keys())
            names.sort(key=lambda name: -types[name])
            for name in names:
                f.write(str(name).rjust(60) + ' ' +
                        str(types[name]).rjust(8) + '\n')

    def start(self, filepath='memprof.txt'):
        """Count the instances of each type, as the baseline for :meth:`check`.

        Parameters
        ----------
        filepath : str, optional
            File to write the counts to, here and in later calls to :meth:`check`.
            Default 'memprof.txt'.
        """
        self.filepath = filepath
        self.initial_counts = self.count_types()

    def check(self):
        """Write the change in the instance count of each type since :meth:`start`.

        The file named in :meth:`start` is overwritten.

        Returns
        -------
        bool
            Always True.
        """
        diffs = {}
        types = self.count_types()
        for type_ in types:
            try:
                diffs[type_] = types[type_] - self.initial_counts[type_]
            except KeyError:
                diffs[type_] = types[type_]
        self.write_to_file(diffs)
        return True


_memory_profiler = MemoryProfiler()
start = _memory_profiler.start
check = _memory_profiler.check
