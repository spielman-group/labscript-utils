#####################################################################
#                                                                   #
# /tests/test_link_indicator.py                                     #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
"""A link indicator following a real server as it answers and then goes away."""
import time

from qtutils.qt.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

from labscript_utils.ls_zprocess import ZMQClient, ZMQServer
from labscript_utils.qtwidgets.link_indicator import LinkIndicator, LinkMonitor


_qapplication = None


def wait_until(condition):
    # qtutils posts even a call made on the GUI thread as an event, so nothing
    # reaches the labels until the events are processed.
    deadline = time.monotonic() + 10
    while not condition():
        if time.monotonic() > deadline:
            raise TimeoutError('The condition did not hold within 10 s.')
        QApplication.processEvents()
        time.sleep(0.01)


def test_indicator_follows_a_server_answering_and_then_gone():
    global _qapplication
    if QApplication.instance() is None:
        # Held for the life of the process: a QApplication that is garbage
        # collected takes every widget built under it down with it.
        _qapplication = QApplication([])
    server = ZMQServer()
    client = ZMQClient(host='localhost', port=server.port)
    icon_label, text_label = QLabel(), QLabel()
    window = QWidget()
    QHBoxLayout(window).addWidget(text_label)
    indicator = LinkIndicator(icon_label, 'Shots', text_label, host='localhost')
    monitor = LinkMonitor(
        lambda: client.say_hello(timeout=1),
        lambda ok, answer: indicator.show_link(ok, None if ok else answer),
        interval=0.1,
    )
    monitor.start()
    try:
        try:
            wait_until(lambda: text_label.text() == 'Responding')
            assert icon_label.toolTip() == 'Shots is responding\nHost: localhost'
        finally:
            server.shutdown()
        wait_until(lambda: text_label.text() == 'Not responding')
        assert icon_label.toolTip().startswith(
            'Shots is not responding\nHost: localhost\n'
        )
    finally:
        monitor.shutdown()
