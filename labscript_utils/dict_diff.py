#####################################################################
#                                                                   #
# /dict_diff.py                                                     #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript_utils, in the labscript suite  #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import numpy as np

def dict_diff(dict1, dict2):
    """Return the difference between two dictionaries as a dictionary of key: [val1, val2] pairs.
    Keys unique to either dictionary are included as key: [val1, '-'] or key: ['-', val2]."""
    diff = {}
    for key in sorted(dict1.keys() & dict2.keys()):
        value1, value2 = dict1[key], dict2[key]
        # array_equal compares shape as well, and never raises on a mismatch.
        if np.iterable(value1) or np.iterable(value2):
            equal = np.array_equal(value1, value2)
        else:
            equal = value1 == value2
        if not equal:
            diff[key] = [value1, value2]
    diff.update({key: [value, '-'] for key, value in dict1.items() if key not in dict2})
    diff.update({key: ['-', value] for key, value in dict2.items() if key not in dict1})
    return diff
