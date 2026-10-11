#####################################################################
#                                                                   #
# __init__.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import h5py
import numpy as np


def get_shot_globals(filepath):
    """Return the evaluated globals of a shot, for use by labscript or lyse.

    Reading them through here applies, in one place, the conversions that plain
    attribute access would not.

    Parameters
    ----------
    filepath : str or pathlib.Path
        The shot file.

    Returns
    -------
    dict
        Global names and values. Numpy bools and strings become Python ones,
        null HDF5 references become None, and bytes are decoded to str.
    """
    params = {}
    with h5py.File(filepath, 'r') as f:
        for name, value in f['globals'].attrs.items():
            # Convert numpy bools to normal bools:
            if isinstance(value, np.bool_):
                value = bool(value)
            # Convert null HDF references to None:
            if isinstance(value, h5py.Reference) and not value:
                value = None
            # Convert numpy strings to Python ones.
            # DEPRECATED, for backward compat with old files.
            if isinstance(value, np.str_):
                value = str(value)
            if isinstance(value, bytes):
                value = value.decode()
            params[name] = value
    return params
