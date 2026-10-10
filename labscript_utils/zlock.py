#####################################################################
#                                                                   #
# zlock.py                                                          #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Script to run a zlock server configured according to LabConfig. Run with:

.. code-block:: bash

    python -m labscript_utils.zlock [--daemon]

If --daemon is specified, the zlock server will be started in the background.
"""
from socket import gethostbyname
from labscript_utils.ls_zprocess import get_config, run_server

def main():
    config = get_config()

    if gethostbyname(config['zlock_host']) != gethostbyname('localhost'):
        msg = (
            "Zlock not configured to run on this host according to labconfig: "
            + "zlock_host=%s" % config['zlock_host']
        )
        raise ValueError(msg)

    run_server('zlock', config['zlock_port'])


if __name__ == '__main__':
    main()
