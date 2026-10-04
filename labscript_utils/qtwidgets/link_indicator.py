#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/link_indicator.py                      #
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
"""Indicator and monitor that show whether a remote application is answering."""
import threading

# Imported for its side effect of registering the :/qtutils/fugue icons.
import qtutils.icons
from qtutils import inmain_decorator, inmain_later
from qtutils.qt import QtCore, QtGui


class LinkIndicator:
    """An icon and tooltip that show whether a remote application is answering.

    It shows a checking state until the first call to ``show_link``. ``show_link``
    and ``show_state`` may be called from any thread, and take effect when the GUI
    thread next processes events, even when called on it.

    Parameters
    ----------
    icon_label : QLabel
        Displays the icon and carries the tooltip.
    name : str
        What the tooltip calls the remote application.
    text_label : QLabel, optional
        Displays a short status beside the icon.
    host : str, optional
        The machine the remote application runs on, given in the tooltip.
    """

    def __init__(self, icon_label, name, text_label=None, host=None):
        self.icon_label = icon_label
        self.name = name
        self.text_label = text_label
        self.host = host
        self.reachable = None
        self.reason = None
        self.state = None
        self.details = ()
        self._redraw()

    @inmain_decorator(wait_for_return=False)
    def show_link(self, reachable, reason=None):
        """Show whether the remote application is answering.

        Parameters
        ----------
        reachable : bool
            Whether it answered.
        reason : str, optional
            Why it did not, given in the tooltip.
        """
        self.reachable = bool(reachable)
        self.reason = reason
        self._redraw()

    @inmain_decorator(wait_for_return=False)
    def show_state(self, state, details=()):
        """Show what the remote application is doing.

        The state and details are kept, and shown whenever the application is
        answering, including again after an outage.

        Parameters
        ----------
        state : str
            Shown in the text label while the application answers. Until one is
            given, the label reads ``Responding``.
        details : iterable of str, optional
            Lines added to the tooltip while the application answers.
        """
        self.state = state
        self.details = tuple(details)
        self._redraw()

    def _redraw(self):
        host_lines = [] if self.host is None else [f'Host: {self.host}']
        if self.reachable is None:
            icon = ':/qtutils/fugue/hourglass'
            text = 'Checking...'
            lines = [f'Checking {self.name}...']
        elif self.reachable:
            icon = ':/qtutils/fugue/tick'
            text = 'Responding' if self.state is None else self.state
            lines = [f'{self.name} is responding', *host_lines, *self.details]
        else:
            icon = ':/qtutils/fugue/exclamation'
            text = 'Not responding'
            lines = [f'{self.name} is not responding', *host_lines]
            if self.reason is not None:
                lines.append(self.reason)
        self.icon_label.setPixmap(QtGui.QIcon(icon).pixmap(QtCore.QSize(16, 16)))
        self.icon_label.setToolTip('\n'.join(lines))
        if self.text_label is not None:
            self.text_label.setText(text)


class LinkMonitor:
    """Probe a remote application on an interval, and report whether it answers.

    Parameters
    ----------
    probe : callable
        Called with no arguments in a background thread. The caller supplies it, for
        example ``RunmanagerClient(timeout=1).say_hello`` or
        ``BlacsClient(timeout=1).get_status``.
    on_status : callable
        Called on the GUI thread as ``on_status(reachable, answer)``. A probe that
        returns is reported as ``(True, answer)``, and one that raises as
        ``(False, message)``.
    interval : float, optional
        Seconds to wait after each probe before the next.

    Examples
    --------
    >>> monitor = LinkMonitor(
    ...     client.say_hello,
    ...     lambda ok, answer: indicator.show_link(ok, None if ok else answer),
    ... )
    >>> monitor.start()
    """

    def __init__(self, probe, on_status, interval=2):
        self.probe = probe
        self.on_status = on_status
        self.interval = interval
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        """Start probing, with the first probe at once."""
        self.thread.start()

    def shutdown(self):
        """Stop probing, without waiting for a probe in flight.

        Called on the GUI thread, it ensures ``on_status`` is not called afterwards.
        """
        # Not joined: a probe in flight can take its whole timeout, and the GUI
        # thread calling this would freeze waiting for it. The daemon thread holds
        # nothing to flush, and an answer arriving after this is dropped.
        self.stopped.set()

    def _run(self):
        while not self.stopped.is_set():
            try:
                reachable, answer = True, self.probe()
            except Exception as exc:
                reachable, answer = False, str(exc)
            inmain_later(self._report, reachable, answer)
            self.stopped.wait(self.interval)

    def _report(self, reachable, answer):
        # Checked here, on the GUI thread, so nothing is reported after shutdown().
        if not self.stopped.is_set():
            self.on_status(reachable, answer)
