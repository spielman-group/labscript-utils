#####################################################################
#                                                                   #
# remote.py                                                         #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Script to run a zprocess.remote server configured according to LabConfig. Run with:

.. code-block:: bash

    python -m labscript_utils.remote [--daemon] [--no-tui]

If --daemon is specified, the server will be started in the background. 
If --no-tui is specified, the server will run with ordinary terminal output 
instead of with the interactive text-based user interface (TUI).
"""
from labscript_utils.ls_zprocess import get_config, run_server


def main():
    run_server('remote', get_config()['zprocess_remote_port'], tui=True)

if __name__ == '__main__':
    main()
