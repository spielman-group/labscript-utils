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
"""Show unhandled exceptions, including those in threads, in an error window.

Importing this module installs ``tkhandler`` as ``sys.excepthook`` and routes
exceptions in threads to it. ``set_logger`` makes it log them too.
"""

import sys
import os
import threading
import traceback
import subprocess
import warnings

# After this many error windows are open, one more is shown, saying there are too many
# errors, and no others until some are closed:
MAX_WINDOWS = 10

# LABSCRIPT_NO_ERROR_DIALOG=1 stops exceptions spawning graphical error windows;
# they are still logged and printed. It is read once, here, so a test of the
# dialog assigns this global instead of setting the variable.
NO_ERROR_DIALOG = os.environ.get('LABSCRIPT_NO_ERROR_DIALOG') == '1'

subprocess_script_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'tk_exception.py'
)


class l:
    logger = None


child_processes = []
_original_showwarning = warnings.showwarning


def install_thread_excepthook():
    """Route exceptions in threads to ``sys.excepthook``, which threads do not call.

    Called when this module is imported, so import it before creating any threads.
    """
    run_old = threading.Thread.run

    def run(*args, **kwargs):
        try:
            run_old(*args, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            if sys is None:
                # Interpreter is shutting down. Don't display graphical error.
                # Let the threading module's code handle this however it normally does.
                raise
            exc_type, exc_value, exc_traceback = sys.exc_info()
            # Cull the top frame so the user doesn't see this wrapping code in their
            # traceback.
            exc_traceback = exc_traceback.tb_next
            sys.excepthook(exc_type, exc_value, exc_traceback)
    threading.Thread.run = run


def tkhandler(exceptclass, exception, exec_info, reraise=True):
    """Log an exception and show it in a graphical error window.

    This is installed as ``sys.excepthook``. The window is a subprocess running
    ``tk_exception.py``, and is not shown if ``NO_ERROR_DIALOG`` is true. Once
    ``MAX_WINDOWS`` windows are open, one more says that further errors will not be
    shown graphically until some are closed. ``KeyboardInterrupt`` and
    ``SystemExit`` are not shown in a window.

    Parameters
    ----------
    exceptclass : type
        The exception's class.
    exception : BaseException
        The exception.
    exec_info : traceback
        The exception's traceback.
    reraise : bool, optional
        Whether to also print the exception with ``sys.__excepthook__``. Default
        True.
    """
    script = os.path.basename(sys.argv[0])
    if not script:
        script = 'python interactive shell'
    shortmessage = f'{exceptclass.__name__}: {exception}'
    longmessage = ''.join(traceback.format_exception(exceptclass, exception, exec_info))
    if l.logger:
        l.logger.error(f'Got an exception:\n{longmessage}')
    if exceptclass in [KeyboardInterrupt, SystemExit]:
        sys.__excepthook__(exceptclass, exception, exec_info)
    else:
        if not NO_ERROR_DIALOG:
            for previous_process in child_processes[:]:
                if previous_process.poll() is not None:
                    child_processes.remove(previous_process)
            if len(child_processes) >= MAX_WINDOWS:
                shortmessage = "Too many errors"
                longmessage = ("Too many errors: Further errors will " +
                               "not be shown graphically until some error windows are closed")
            if len(child_processes) < MAX_WINDOWS + 1:
                process = subprocess.Popen(
                    [sys.executable, subprocess_script_path, script, shortmessage, longmessage]
                )
                child_processes.append(process)
        if reraise:
            sys.__excepthook__(exceptclass, exception, exec_info)


def logwarning(message, category, filename, lineno, file=None, line=None):
    """Log a warning with ``l.logger``, then show it as Python normally does.

    This replaces ``warnings.showwarning`` once :func:`set_logger` is called.
    """
    logmessage = warnings.formatwarning(message, category, filename, lineno, line)
    l.logger.warning(logmessage)
    _original_showwarning(message, category, filename, lineno, file, line)


def set_logger(logger):
    """Log exceptions and warnings with ``logger``.

    Parameters
    ----------
    logger : logging.Logger
    """
    l.logger = logger
    warnings.showwarning = logwarning


# Fail at import, not later, if tkinter is missing: some Debian Pythons omit it.
import tkinter
sys.excepthook = tkhandler
install_thread_excepthook()
