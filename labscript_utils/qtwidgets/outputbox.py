#####################################################################
#                                                                   #
# qtwidgets/outputbox.py                                            #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

import qtutils.outputbox

from labscript_utils.ls_zprocess import Context


class OutputBox(qtutils.outputbox.OutputBox):
    """A qtutils OutputBox that listens on all network interfaces.

    It uses the suite's secure ZMQ Context, so insecure messages from external
    addresses are discarded. See qtutils.outputbox.OutputBox for the rest of its
    interface.

    Parameters
    ----------
    container : QLayout or QSplitter
        Anything with an ``addWidget`` method; the output's text widget is added
        to it.
    scrollback_lines : int, optional
        The number of lines of output to keep.
    """

    def __init__(self, container, scrollback_lines=1000):
        context = Context.instance()
        # Our Context is a SecureContext, so it can listen on public interfaces.
        super().__init__(
            container=container,
            scrollback_lines=scrollback_lines,
            zmq_context=context,
            bind_address='tcp://*',
        )
