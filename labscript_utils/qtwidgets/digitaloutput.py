#####################################################################
#                                                                   #
# digitaloutput.py                                                  #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from qtutils.qt import QtWidgets

from .lockable import LockableOutput


class DigitalOutput(LockableOutput, QtWidgets.QPushButton):
    """A checkable button that shows and sets a BLACS digital output.

    Right-clicking it offers to lock it. Its ``state`` is whether it is checked.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The button filters its own events, so that a right-click menu opens
        # even while it is disabled.
        self.installEventFilter(self)
        self.setCheckable(True)
        self._output = None

    def set_DO(self, DO, notify_old_DO=True, notify_new_DO=True, inverted=False):
        """Put a BLACS digital output in charge of this button.

        Nothing is notified when ``DO`` is the output already in charge.

        Parameters
        ----------
        DO : DigitalOut or None
            The output to put in charge, or None for none.
        notify_old_DO : bool, optional
            Whether to remove this button from the output that was in charge.
        notify_new_DO : bool, optional
            Whether to add this button to ``DO``.
        inverted : bool, optional
            Passed to ``DO.add_widget``: whether the button shows the opposite of
            the output's state.
        """
        if DO != self._output:
            if self._output is not None and notify_old_DO:
                self._output.remove_widget(self)
            if DO is not None and notify_new_DO:
                DO.add_widget(self, inverted)
        self._output = DO

    def get_DO(self):
        """Return the BLACS digital output in charge of this button, or None."""
        return self._output

    @property
    def _lock_target(self):
        return self

    @property
    def state(self):
        """bool: whether the button is checked."""
        return self.isChecked()

    @state.setter
    def state(self, state):
        # int() before bool() accepts '1' and '0' as well as booleans and 0 and 1.
        self.setChecked(bool(int(state)))


class InvertedDigitalOutput(DigitalOutput):
    """A DigitalOutput that shows the opposite of its output's state."""

    def set_DO(self, DO, notify_old_DO=True, notify_new_DO=True, inverted=True):
        super().set_DO(DO, notify_old_DO, notify_new_DO, inverted)

    @property
    def state(self):
        return not DigitalOutput.state.fget(self)

    @state.setter
    def state(self, state):
        DigitalOutput.state.fset(self, not state)
