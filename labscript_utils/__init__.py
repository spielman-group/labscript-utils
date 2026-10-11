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

import sys
import os
import importlib

from .versions import VersionException, check_version, package_version

__version__ = package_version(__package__)

from labscript_profile import LABSCRIPT_SUITE_PROFILE

if not os.path.exists(LABSCRIPT_SUITE_PROFILE):
    from labscript_profile.create import create_profile
    create_profile()
    # This would normally run at interpreter startup but didn't since the profile didn't
    # exist:
    import labscript_profile
    labscript_profile.add_userlib_and_pythonlib()


labscript_utils_dir = os.path.dirname(os.path.realpath(__file__))


def import_or_reload(modulename):
    """Import a module, rerunning its code if it is already loaded.

    Otherwise this behaves as ``import modulename`` would.

    Parameters
    ----------
    modulename : str
        Name of the module to import.

    Returns
    -------
    module
        The imported or reloaded module.
    """
    if modulename in sys.modules.keys():
        importlib.reload(sys.modules[modulename])
        return sys.modules[modulename]
    module = importlib.import_module(modulename)
    return module


def dedent(s):
    """Unwrap a multiline triple-quoted string, such as an error message.

    Removes leading spaces from the first line, all common leading indentation
    (spaces only) from subsequent lines, and trailing spaces from all lines, and
    replaces single newlines prior to lines with the common indentation with
    spaces. Lines with additional indentation are kept verbatim.

    Parameters
    ----------
    s : str
        The string to unwrap.

    Returns
    -------
    str
        The unwrapped string.
    """
    lines = [line.rstrip(' ') for line in s.splitlines()]
    indentation = float('inf')
    for line in lines[1:]:
        if line:
            indentation = min(indentation, len(line) - len(line.lstrip(' ')))
    if not lines[1:]:
        indentation = 0
    dedented_lines = []
    for i, line in enumerate(lines):
        if i == 0:
            dedented_line = line.lstrip(' ')
        else:
            dedented_line = line[indentation:]
        dedented_lines.append(dedented_line)
    unwrapped_lines = []
    for i, line in enumerate(dedented_lines):
        if i == 0:
            unwrapped_lines.append(line)
        else:
            previous_line = dedented_lines[i - 1]
            # If either this line or the previous line is blank or starts with custom
            # indentation, put this line on a newline rather than unwrapping it:
            if any(not l or l.startswith(' ') for l in [line, previous_line]):
                unwrapped_lines.append('\n' + line)
            else:
                unwrapped_lines.append(' ' + line)
    return ''.join(unwrapped_lines)


def ensure_str(s):
    """Return ``s`` as a ``str``, decoding it if it is ``bytes``.

    HDF5 strings are often ``bytes``.

    Parameters
    ----------
    s : bytes or object
        The value to convert; anything other than ``bytes`` is passed to ``str``.

    Returns
    -------
    str
    """
    return s.decode() if isinstance(s, bytes) else str(s)


# Enforce that the same file can't be imported under multiple names, to help
# prevent subtle bugs:
import labscript_utils.double_import_denier
labscript_utils.double_import_denier.enable()

# Disable the 'quick edit' feature of Windows' cmd.exe, which causes console applicatons
# to freeze if their console windows are merely clicked on. This causes all kinds of
# headaches, so we disable it in all labscript programs:
import zprocess
zprocess.disable_quick_edit()
