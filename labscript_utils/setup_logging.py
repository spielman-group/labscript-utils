#####################################################################
#                                                                   #
# /setup_logging.py                                                 #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import logging
import os
import sys
import warnings
from io import UnsupportedOperation

from labscript_profile import LABSCRIPT_SUITE_PROFILE
from labscript_utils.ls_zprocess import Handler, ensure_connected_to_zlog

LOG_PATH = os.path.join(LABSCRIPT_SUITE_PROFILE, 'logs')


class LessThanFilter(logging.Filter):
    """A filter that passes only records with a level below ``less_than``."""

    def __init__(self, less_than):
        self.less_than = less_than
        super().__init__()

    def filter(self, record):
        return record.levelno < self.less_than


def setup_logging(
    program_name,
    log_level=logging.DEBUG,
    terminal_level=logging.INFO,
    maxBytes=1024*1024*50,
    backupCount=1,
):
    """Log a program's messages to its log file and to the terminal.

    Call it once per program. The logger named ``program_name`` loses its previous
    handlers and gets one that writes ``LOG_PATH/<program_name>.log`` through the
    zlog server, which is started if it is not running. Where stdout is available
    it also gets handlers for the terminal: stdout below WARNING, and stderr for
    WARNING and above. It returns the logger, at level DEBUG.

    Parameters
    ----------
    log_level, terminal_level : int, optional
        The levels of the log file's handler and of the stdout handler.
    maxBytes, backupCount : int, optional
        Ignored. They are labconfig settings of the zlog server, and stay in the
        signature for callers that still pass them.
    """
    ensure_connected_to_zlog()
    logger = logging.getLogger(program_name)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    if not os.path.exists(LOG_PATH):
        os.mkdir(LOG_PATH)

    # The name lets a subprocess's handler use its parent's log path, so zlog makes
    # no unrelated log files for computers of one process tree installed in
    # different places.
    log_path = os.path.join(LOG_PATH, f'{program_name}.log')
    handler = Handler(log_path, name=program_name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    try:
        # fileno() is needed below. It raises in Jupyter notebooks, where log
        # messages are then not printed to stdout or stderr.
        stdout_fileno = sys.stdout.fileno() if sys.stdout is not None else -1
    except UnsupportedOperation:
        warnings.warn(
            "Logging to stdout and stderr is disabled. "
            "See the log files for log messages."
        )
    else:
        if sys.stdout is not None and stdout_fileno >= 0:
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setFormatter(formatter)
            stdout_handler.setLevel(terminal_level)
            logger.addHandler(stdout_handler)
            if sys.stderr is not None and sys.stderr.fileno() >= 0:
                # Send warnings and greater to stderr instead of stdout:
                stdout_handler.addFilter(LessThanFilter(logging.WARNING))
                stderr_handler = logging.StreamHandler(sys.stderr)
                stderr_handler.setFormatter(formatter)
                stderr_handler.setLevel(logging.WARNING)
                logger.addHandler(stderr_handler)
        else:
            # Prevent bug on windows where writing to stdout without a command
            # window causes a crash:
            sys.stdout = sys.stderr = open(os.devnull, 'w')
    logger.setLevel(logging.DEBUG)
    return logger
