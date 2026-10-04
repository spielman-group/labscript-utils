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
"""A widget that keeps asking a remote application, and shows whether it answers."""
import threading

# Imported for its side effect of registering the :/qtutils/fugue icons.
import qtutils.icons
from qtutils import inmain_decorator, inmain_later
from qtutils.qt import QtCore, QtGui, QtWidgets

from labscript_utils.qtwidgets.elide_label import elide_label


class LinkIndicator(QtWidgets.QWidget):
    """An icon and status that show whether a remote application is answering.

    Once started, it asks the application with ``probe`` on a background thread,
    showing checking until the first answer; one never started can be shown
    disabled instead. The status is one line, elided to the room it has, with the
    whole status shown on hover. ``show_state`` and ``show_disabled`` may be called
    from any thread, and take effect when the GUI thread next processes events,
    even when called on it.

    Parameters
    ----------
    name : str
        What the tooltip calls the remote application.
    probe : callable
        Called with no arguments in a background thread. A return shows the
        application answering, and an exception shows it not answering, so give it
        a short deadline: for example ``lambda: client.say_hello(timeout=1)`` or
        ``BlacsClient(timeout=1).get_status``.
    host : str, optional
        The machine the remote application runs on, given in the tooltip.
    interval : float, optional
        Seconds to wait after each probe before the next.
    on_answer : callable, optional
        Called on the GUI thread as ``on_answer(reachable, answer)`` after each
        answer is shown: ``True`` and what ``probe`` returned, or ``False`` and the
        exception's message.
    parent : QWidget, optional

    Examples
    --------
    >>> indicator = LinkIndicator('BLACS', BlacsClient(timeout=1).get_status)
    >>> ui.blacs_link_layout.addWidget(indicator)
    >>> indicator.start()
    """

    def __init__(self, name, probe, host=None, interval=2, on_answer=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.probe = probe
        self.host = host
        self.interval = interval
        self.on_answer = on_answer
        self.icon_label = QtWidgets.QLabel()
        self.text_label = QtWidgets.QLabel()
        self.text_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        elide_label(self.text_label, layout, QtCore.Qt.TextElideMode.ElideRight)
        self.disabled = False
        self.reachable = None
        self.reason = None
        self.state = None
        self.details = ()
        self.stopped = threading.Event()
        self.probe_thread = threading.Thread(target=self._run, daemon=True)
        self._redraw()

    def start(self):
        """Start probing, with the first probe at once."""
        self.probe_thread.start()

    def shutdown(self):
        """Stop probing, without waiting for a probe in flight.

        Called on the GUI thread, it ensures no later answer is shown or passed to
        ``on_answer``.
        """
        # Not joined: a probe in flight can take its whole timeout, and the GUI
        # thread calling this would freeze waiting for it. The daemon thread holds
        # nothing to flush, and an answer arriving after this is dropped.
        self.stopped.set()

    @inmain_decorator(wait_for_return=False)
    def show_state(self, state, details=()):
        """Show what the remote application is doing.

        The state and details are kept, and shown whenever the application is
        answering, including again after an outage.

        Parameters
        ----------
        state : str or None
            Shown as the status while the application answers. While it is None,
            the status reads ``Responding``.
        details : iterable of str, optional
            Lines added to the tooltip while the application answers.
        """
        self.state = state
        self.details = tuple(details)
        self._redraw()

    @inmain_decorator(wait_for_return=False)
    def show_disabled(self, reason=None):
        """Grey the indicator out, with no icon, until the next answer.

        An indicator that is never started stays disabled.

        Parameters
        ----------
        reason : str, optional
            Why the remote application is not being checked, given in the tooltip.
        """
        self.disabled = True
        self.reason = reason
        self._redraw()

    def _run(self):
        while not self.stopped.is_set():
            try:
                reachable, answer = True, self.probe()
            except Exception as exc:
                reachable, answer = False, str(exc)
            inmain_later(self._show_answer, reachable, answer)
            self.stopped.wait(self.interval)

    def _show_answer(self, reachable, answer):
        # Checked here, on the GUI thread, so nothing is shown after shutdown().
        if self.stopped.is_set():
            return
        self.disabled = False
        self.reachable = reachable
        self.reason = None if reachable else answer
        self._redraw()
        if self.on_answer is not None:
            self.on_answer(reachable, answer)

    def _redraw(self):
        host_lines = [] if self.host is None else [f'Host: {self.host}']
        reason_lines = [] if self.reason is None else [self.reason]
        if self.disabled:
            icon = None
            text = 'Disabled'
            lines = [f'Not checking {self.name}', *reason_lines]
        elif self.reachable is None:
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
            lines = [f'{self.name} is not responding', *host_lines, *reason_lines]
        if icon is None:
            self.icon_label.clear()
        else:
            self.icon_label.setPixmap(QtGui.QIcon(icon).pixmap(QtCore.QSize(16, 16)))
        tooltip = '\n'.join(lines)
        self.icon_label.setToolTip(tooltip)
        # elide_label shows one line, so a multi-line state is joined into one. With
        # no icon to hover, a disabled indicator's text carries the tooltip instead.
        self.text_label.setText(' '.join(text.splitlines()))
        self.text_label.setToolTip(tooltip if self.disabled else text)
        self.setEnabled(not self.disabled)
