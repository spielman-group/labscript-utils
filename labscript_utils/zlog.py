#####################################################################
#                                                                   #
# zlog.py                                                           #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Script to run a zlog server configured according to LabConfig. Run with:

.. code-block:: bash

    python -m labscript_utils.zlog [--daemon]

If --daemon is specified, the zlog server will be started in the background.
"""
from labscript_utils.ls_zprocess import get_config, run_server


def main():
    config = get_config()

    run_server(
        'zlog',
        config['zlog_port'],
        '--cls', 'RotatingFileHandler',
        '--maxBytes', str(config['logging_maxBytes']),
        '--backupCount', str(config['logging_backupCount']),
    )


if __name__ == '__main__':
    main()
