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

:func:`install` sets ``tkhandler`` as ``sys.excepthook`` and routes exceptions in
threads to it. Importing this module still calls it. ``set_logger`` makes it log them
too.
"""

import logging
import sys
import os
import threading
import traceback
import subprocess
import warnings

# After this many error windows are open, one more is shown, saying there are too many
# errors, and no others until some are closed:
MAX_WINDOWS = 10

# If this environment variable is set to a value other than '' or '0', exceptions are
# printed to stderr instead of being shown in a window:
DISABLE_ENV_VAR = 'LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK'

subprocess_script_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'tk_exception.py'
)


class l:
    logger = None


child_processes = []
_installed = False
# Set by install(), so a test of the window assigns it instead:
_show_windows = False
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

    :func:`install` sets it as ``sys.excepthook``. The window is a subprocess running
    ``tk_exception.py``. It is not shown if ``DISABLE_ENV_VAR`` is set or tkinter is
    missing, when the exception is always printed. Once ``MAX_WINDOWS`` windows are
    open, one more says that further errors will not be shown graphically until some
    are closed. ``KeyboardInterrupt`` and ``SystemExit`` are not shown in a window.

    Parameters
    ----------
    exec_info : traceback
        The exception's traceback.
    reraise : bool, optional
        Whether to also print the exception with ``sys.__excepthook__``.
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
        if not _show_windows:
            reraise = True
        else:
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
    """Log a warning with ``l.logger``, instead of printing it.

    This replaces ``warnings.showwarning`` once :func:`set_logger` is called.
    """
    logmessage = warnings.formatwarning(message, category, filename, lineno, line)
    l.logger.warning(logmessage)


def set_logger(logger):
    """Log exceptions with ``logger``, and warnings too if it logs WARNING.

    A logger that does not, as with logging off in the labconfig, leaves warnings
    printed as Python normally does.
    """
    l.logger = logger
    if logger.isEnabledFor(logging.WARNING):
        warnings.showwarning = logwarning
    else:
        warnings.showwarning = _original_showwarning


def install():
    """Set ``sys.excepthook`` to :func:`tkhandler`, and send uncaught exceptions in
    threads to it.

    Exceptions are printed instead of shown in a window if tkinter is not installed,
    or if the environment variable ``LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK`` is set to
    a value other than '' or '0'. Calls after the first do nothing.
    """
    global _installed, _show_windows
    if _installed:
        return
    _installed = True
    if os.environ.get(DISABLE_ENV_VAR, '') in ('', '0'):
        # tkinter is part of the standard library but is a separate package on Debian
        # and Ubuntu, so it may be missing:
        try:
            import tkinter
        except ImportError:
            warnings.warn(
                "tkinter is not installed, so exceptions will be printed to stderr "
                "instead of being shown in a window. Install the python3-tk package for "
                "the error windows."
            )
        else:
            _show_windows = True
    sys.excepthook = tkhandler
    install_thread_excepthook()


# TODO: remove this call in a future release, so that importing this module does not
# install the handler. Programs that use the handler call install() themselves.
install()
