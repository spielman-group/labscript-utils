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
import sys, os
from io import UnsupportedOperation
import logging, logging.handlers
import warnings
from labscript_utils.ls_zprocess import Handler, ensure_connected_to_zlog


from labscript_profile import LABSCRIPT_SUITE_PROFILE

LOG_PATH = os.path.join(LABSCRIPT_SUITE_PROFILE, 'logs')

class LessThanFilter(logging.Filter):
    def __init__(self, less_than):
        self.less_than = less_than
        logging.Filter.__init__(self)
    def filter(self, record):
        return record.levelno < self.less_than


def setup_logging(program_name, log_level=logging.DEBUG, terminal_level=logging.INFO, maxBytes=1024*1024*50, backupCount=1):
    # maxBytes and backupCount are ignored: they are labconfig settings of the zlog
    # server. They stay in the signature for callers that still pass them.
    ensure_connected_to_zlog()
    logger = logging.getLogger(program_name)
    # Clear any previously added handlers from the logger:
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Make sure the logging directory exists:
    if not os.path.exists(LOG_PATH):
        os.mkdir(LOG_PATH)

    # The name lets a subprocess's handler use its parent's log path, so zlog makes no
    # unrelated log files for computers of one process tree installed in different places.
    log_path = os.path.join(LOG_PATH, '%s.log' % program_name)
    handler = Handler(log_path, name=program_name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    logger.addHandler(handler)
    try:
        # Check that sys.stdout.fileno is callable, which is needed below. It is NOT
        # callable in Jupyter notebooks.
        stdout_fileno = sys.stdout.fileno()
    except UnsupportedOperation:
        # In this case the code is likely being run from a Jupyter notebook, warn the
        # user that log messages won't be printed to stdout or stderr.
        warnings.warn(
            "Logging to stdout and stderr is disabled. See the log files for log messages."
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
                sterr_handler = logging.StreamHandler(sys.stderr)
                sterr_handler.setFormatter(formatter)
                sterr_handler.setLevel(logging.WARNING)
                logger.addHandler(sterr_handler)
        else:
            # Prevent bug on windows where writing to stdout without a command
            # window causes a crash:
            sys.stdout = sys.stderr = open(os.devnull, 'w')
    logger.setLevel(logging.DEBUG)
    return logger
