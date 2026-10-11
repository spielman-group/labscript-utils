#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/lockable.py                            #
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
from qtutils.qt import QtCore, QtGui, QtWidgets


class LockableOutput:
    """Mixin for an output widget that a right-click menu locks and unlocks.

    List it before the widget's Qt base class. The widget installs itself as its
    own event filter, so that the menu opens while its target is disabled and a
    disabled widget passes scroll-wheel events to its parent. A subclass must set
    ``_lock_target``, the widget that locking disables, and ``_output``, its BLACS
    output or None.
    """

    @property
    def lock_state(self):
        """True while the lock target is disabled."""
        return not self._lock_target.isEnabled()

    def popup_lock_menu(self, source, pos):
        """Pop up the lock menu for ``source``, a widget of this output, at ``pos``."""
        menu = QtWidgets.QMenu(source)
        menu.addAction("Unlock" if self.lock_state else "Lock")
        menu.triggered.connect(self._menu_triggered)
        menu.popup(source.mapToGlobal(pos))

    def eventFilter(self, obj, event):
        if (event.type() == QtCore.QEvent.Type.MouseButtonRelease
                and event.button() == QtCore.Qt.MouseButton.RightButton):
            self.popup_lock_menu(self, event.pos())
        # Pass scroll-wheel events of a disabled widget to its parent. Adapted from
        # http://www.qtforum.org/article/28540/disabled-widgets-and-wheel-events.html
        elif obj and not obj.isEnabled() and event.type() == QtCore.QEvent.Type.Wheel:
            new_event = QtGui.QWheelEvent(
                QtCore.QPointF(obj.mapToParent(event.position().toPoint())),
                event.globalPosition(),
                event.pixelDelta(), event.angleDelta(),
                event.buttons(), event.modifiers(),
                event.phase(), event.inverted(),
            )
            QtWidgets.QApplication.instance().postEvent(obj.parent(), new_event)
            return True
        return super().eventFilter(obj, event)

    def _menu_triggered(self, action):
        if action.text() == "Lock":
            self.lock()
        elif action.text() == "Unlock":
            self.unlock()

    def lock(self, notify_output=True):
        """Disable the widget, and notify its BLACS output if ``notify_output``."""
        self._lock_target.setEnabled(False)
        if self._output is not None and notify_output:
            self._output.lock()

    def unlock(self, notify_output=True):
        """Enable the widget, and notify its BLACS output if ``notify_output``."""
        self._lock_target.setEnabled(True)
        if self._output is not None and notify_output:
            self._output.unlock()
