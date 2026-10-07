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
import functools
import threading

# Imported for its side effect of registering the :/qtutils/fugue icons.
import qtutils.icons
from qtutils import inmain_decorator, inmain_later
from qtutils.qt import QtCore, QtGui, QtWidgets

from labscript_utils.ls_zprocess import ZMQClient
from labscript_utils.qtwidgets.elide_label import elide_label


class LinkIndicator(QtWidgets.QWidget):
    """A remote application's name, link icon and status, showing whether it answers.

    The name and icon share a row, with the status under them. Once started, it
    asks the application on a background thread, with a hello or ``command``,
    showing checking until the first answer. The status is one line, elided to the
    room it has, with the whole status shown on hover. ``show_state`` may be called
    from any thread, and takes effect when the GUI thread next processes events,
    even when called on it.

    It asks through a client of its own, so a caller passes the application's
    address, never a client: zprocess requests from two threads on one client can
    block each other for good.

    Parameters
    ----------
    name : str
        The remote application, as the title and the tooltip name it.
    host : str
        The machine the remote application runs on, also given in the tooltip.
    port : int
        The port the remote application's server listens on.
    command : str, optional
        A request to make in place of a hello, such as ``'get_status'``, for an
        ``on_answer`` that needs its answer.
    interval : float, optional
        Seconds to wait after each probe before the next.
    on_answer : callable, optional
        Called on the GUI thread as ``on_answer(reachable, answer)`` after each
        answer is shown: ``True`` and the server's answer, or ``False`` and the
        exception's message.
    status_width : int, optional
        The indicator's fixed width, in pixels. A longer status is elided.
    parent : QWidget, optional

    Examples
    --------
    >>> indicator = LinkIndicator('lyse', client.host, client.port)
    >>> ui.lyse_link_layout.addWidget(indicator)
    >>> indicator.start()
    """

    def __init__(
        self,
        name,
        host,
        port,
        command=None,
        interval=2,
        on_answer=None,
        status_width=220,
        parent=None,
    ):
        super().__init__(parent)
        self.name = name
        self.host = host
        self._client = ZMQClient(host=host, port=port, timeout=1)
        if command is None:
            self._probe = self._client.say_hello
        else:
            self._probe = functools.partial(self._client.request, command)
        self.interval = interval
        self.on_answer = on_answer
        self.setFixedWidth(status_width)
        self.title_label = QtWidgets.QLabel(name)
        self.icon_label = QtWidgets.QLabel()
        self.text_label = QtWidgets.QLabel()
        self.text_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        title_row = QtWidgets.QHBoxLayout()
        title_row.addWidget(self.title_label)
        title_row.addWidget(self.icon_label)
        title_row.addStretch()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(title_row)
        layout.addWidget(self.text_label)
        elide_label(self.text_label, layout, QtCore.Qt.TextElideMode.ElideRight)
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

    def _run(self):
        while not self.stopped.is_set():
            try:
                reachable, answer = True, self._probe()
            except Exception as exc:
                reachable, answer = False, str(exc)
            inmain_later(self._show_answer, reachable, answer)
            self.stopped.wait(self.interval)

    def _show_answer(self, reachable, answer):
        # Checked here, on the GUI thread, so nothing is shown after shutdown().
        if self.stopped.is_set():
            return
        self.reachable = reachable
        self.reason = None if reachable else answer
        self._redraw()
        if self.on_answer is not None:
            self.on_answer(reachable, answer)

    def _redraw(self):
        host_line = f'Host: {self.host}'
        if self.reachable is None:
            icon = ':/qtutils/fugue/hourglass'
            text = 'Checking...'
            lines = [f'Checking {self.name}...']
        elif self.reachable:
            icon = ':/qtutils/fugue/tick'
            text = 'Responding' if self.state is None else self.state
            lines = [f'{self.name} is responding', host_line, *self.details]
        else:
            icon = ':/qtutils/fugue/exclamation'
            text = 'Not responding'
            lines = [f'{self.name} is not responding', host_line, self.reason]
        self.icon_label.setPixmap(QtGui.QIcon(icon).pixmap(QtCore.QSize(16, 16)))
        self.icon_label.setToolTip('\n'.join(lines))
        # elide_label shows one line, so a multi-line state is joined into one.
        self.text_label.setText(' '.join(text.splitlines()))
        self.text_label.setToolTip(text)
