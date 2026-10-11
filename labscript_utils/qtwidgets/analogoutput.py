#####################################################################
#                                                                   #
# analogoutput.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from qtutils.qt import QtCore, QtGui, QtWidgets

from .lockable import LockableOutput


class NoStealFocusDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """A QDoubleSpinBox that ignores the mouse wheel until it has focus."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

    def focusInEvent(self, event):
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
        return super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        return super().focusOutEvent(event)

    def wheelEvent(self, event):
        if self.hasFocus():
            return super().wheelEvent(event)
        else:
            event.ignore()


class AnalogOutput(LockableOutput, QtWidgets.QWidget):
    """A labelled spin box and unit combo box that show and set a BLACS analog output.

    Parameters
    ----------
    display_name : str, optional
        Label text to show in place of the hardware and connection names.
    horizontal_alignment : bool, optional
        Lay the label, spin box and combo box out in a row rather than a column.
    """

    def __init__(self, hardware_name, connection_name='-', display_name=None,
                 horizontal_alignment=False, parent=None):
        super().__init__(parent)

        self._connection_name = connection_name
        self._hardware_name = hardware_name

        label_text = (
            (self._hardware_name + '\n' + self._connection_name)
            if display_name is None
            else display_name
        )
        self._label = QtWidgets.QLabel(label_text)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self._spin_widget = NoStealFocusDoubleSpinBox()
        self._spin_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self._spin_widget.setKeyboardTracking(False)
        self._lock_target = self._spin_widget
        self._combobox = QtWidgets.QComboBox()
        self._combobox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self._combobox.currentIndexChanged.connect(self._on_combobox_change)

        self._value_changed_function = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum
        )

        # The actions of the spin box's context menu.
        self._lock_action = QtGui.QAction("Lock", self._spin_widget)
        self._lock_action.triggered.connect(lambda: self._menu_triggered(self._lock_action))
        self._stepsize_action = QtGui.QAction("Set step size", self._spin_widget)
        self._stepsize_action.triggered.connect(self._change_step)
        self._stepup_action = QtGui.QAction("Step up", self._spin_widget)
        self._stepup_action.triggered.connect(lambda: self._spin_widget.stepBy(1))
        self._stepdown_action = QtGui.QAction("Step down", self._spin_widget)
        self._stepdown_action.triggered.connect(lambda: self._spin_widget.stepBy(-1))

        self.menu = None

        def delete_menu(menu):
            menu.deleteLater()
            if menu == self.menu:
                self.menu = None

        def context_menu(pos):
            self.menu = menu = self._spin_widget.lineEdit().createStandardContextMenu()
            menu.addSeparator()
            menu.addAction(self._stepup_action)
            menu.addAction(self._stepdown_action)
            # Grey out the step actions at the ends of the range.
            if self._spin_widget.value() == self._spin_widget.minimum():
                self._stepdown_action.setEnabled(False)
            else:
                self._stepdown_action.setEnabled(True)
            if self._spin_widget.value() == self._spin_widget.maximum():
                self._stepup_action.setEnabled(False)
            else:
                self._stepup_action.setEnabled(True)

            menu.addSeparator()
            self._lock_action.setText("Unlock" if self.lock_state else "Lock")
            menu.addAction(self._lock_action)
            menu.addAction(self._stepsize_action)

            # createStandardContextMenu parents each menu to the line edit, so
            # delete it once it is hidden.
            menu.aboutToHide.connect(lambda menu=menu: delete_menu(menu))

            menu.popup(self.mapToGlobal(pos))

        self._spin_widget.lineEdit().setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._spin_widget.lineEdit().customContextMenuRequested.connect(context_menu)

        if horizontal_alignment:
            self._layout = QtWidgets.QHBoxLayout(self)
            self._layout.addWidget(self._label)
            self._layout.addWidget(self._spin_widget)
            self._layout.addWidget(self._combobox)
            self._layout.setContentsMargins(0, 0, 0, 0)
        else:
            self._layout = QtWidgets.QGridLayout(self)
            self._layout.setVerticalSpacing(3)
            self._layout.setHorizontalSpacing(0)
            self._layout.setContentsMargins(3, 3, 3, 3)

            self._label.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                QtWidgets.QSizePolicy.Policy.Minimum,
            )

            h_widget = QtWidgets.QWidget()
            h_layout = QtWidgets.QHBoxLayout(h_widget)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.addWidget(self._spin_widget)
            h_layout.addWidget(self._combobox)

            self._layout.addWidget(self._label, 0, 0)
            self._layout.addWidget(h_widget, 1, 0)
            self._layout.addItem(
                QtWidgets.QSpacerItem(
                    0, 0,
                    QtWidgets.QSizePolicy.Policy.Minimum,
                    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                ),
                2, 0,
            )

        # The widget filters its own events, so that a right-click menu opens
        # even while it is disabled.
        self.installEventFilter(self)
        self._output = None

    def set_AO(self, AO, notify_old_AO=True, notify_new_AO=True):
        """Put a BLACS analog output, or None, in charge of this widget.

        Nothing is notified when ``AO`` is already in charge. Otherwise
        ``notify_old_AO`` and ``notify_new_AO`` choose whether the old output
        removes this widget and the new output adds it.
        """
        if AO != self._output:
            if self._output is not None and notify_old_AO:
                self._output.remove_widget(self, False)
            if AO is not None and notify_new_AO:
                AO.add_widget(self)
        self._output = AO

    def get_AO(self):
        """Return the BLACS analog output in charge of this widget, or None."""
        return self._output

    def connect_value_change(self, func):
        """Call ``func(value, selected_unit, True)`` when the spin box value changes."""
        self._value_changed_function = (
            lambda value, self=self: func(value, self.selected_unit, True)
        )
        self._spin_widget.valueChanged.connect(self._value_changed_function)

    def disconnect_value_change(self):
        """Stop calling the function given to ``connect_value_change``."""
        self._spin_widget.valueChanged.disconnect(self._value_changed_function)

    def set_combobox_model(self, model):
        """Set the model that lists the units in the combo box."""
        self._combobox.setModel(model)

    def _on_combobox_change(self):
        selected_text = self.selected_unit
        if self._output is not None:
            self._output.change_unit(selected_text)

    def block_spinbox_signals(self):
        """Block the spin box's signals, returning whether they were blocked."""
        return self._spin_widget.blockSignals(True)

    def unblock_spinbox_signals(self):
        """Unblock the spin box's signals, returning whether they were blocked."""
        return self._spin_widget.blockSignals(False)

    def set_spinbox_value(self, value, unit):
        """Show ``value``, given in ``unit``, in the selected unit.

        Without a BLACS output in charge, ``value`` is shown as it is.
        """
        if self._output is not None:
            value = self._output.convert_value_to_base(value, unit)
            value = self._output.convert_value_from_base(value, self.selected_unit)
        self._spin_widget.setValue(value)

    @property
    def selected_unit(self):
        """str: the unit selected in the combo box."""
        return str(self._combobox.currentText())

    def block_combobox_signals(self):
        """Block the combo box's signals, returning whether they were blocked."""
        return self._combobox.blockSignals(True)

    def unblock_combobox_signals(self):
        """Unblock the combo box's signals, returning whether they were blocked."""
        return self._combobox.blockSignals(False)

    def set_selected_unit(self, unit):
        """Select ``unit`` in the combo box, if its model lists it."""
        if unit != self.selected_unit:
            item = self._combobox.model().findItems(unit)
            if item:
                model_index = self._combobox.model().indexFromItem(item[0])
                self._combobox.setCurrentIndex(model_index.row())

    def set_num_decimals(self, decimals):
        """Set the number of decimals the spin box shows."""
        self._spin_widget.setDecimals(decimals)

    def set_limits(self, lower, upper):
        """Set the range of the spin box."""
        self._spin_widget.setRange(lower, upper)

    def set_step_size(self, step):
        """Set the spin box's step."""
        self._spin_widget.setSingleStep(step)

    def _change_step(self):
        maximum_step = abs(self._spin_widget.maximum() - self._spin_widget.minimum())
        new_step, ok = QtWidgets.QInputDialog.getDouble(
            self,
            "Set step size",
            "Set step size",
            self._spin_widget.singleStep(),
            0.0,
            maximum_step,
            self._spin_widget.decimals(),
        )

        if ok:
            self.set_step_size(new_step)
            if self._output:
                self._output.set_step_size(new_step, self.selected_unit)
