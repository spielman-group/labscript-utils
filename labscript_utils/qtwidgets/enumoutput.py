#####################################################################
#                                                                   #
# enumcontrol.py                                                    #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from qtutils.qt import QtCore, QtWidgets

from .lockable import LockableOutput


class EnumOutput(LockableOutput, QtWidgets.QWidget):
    """A labelled combo box that shows and sets a BLACS enum output.

    Parameters
    ----------
    display_name : str, optional
        Label text to show in place of the hardware and connection names.
    horizontal_alignment : bool, optional
        Lay the label and combo box out in a row rather than a column.
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
        self._combobox = QtWidgets.QComboBox()
        self._combobox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum
        )
        self._lock_target = self._combobox

        self._value_changed_function = None

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum
        )

        if horizontal_alignment:
            self._layout = QtWidgets.QHBoxLayout(self)
            self._layout.addWidget(self._label)
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

    def set_EO(self, EO, notify_old_EO=True, notify_new_EO=True):
        """Put a BLACS enum output, or None, in charge of this widget.

        Nothing is notified when ``EO`` is already in charge. Otherwise
        ``notify_old_EO`` and ``notify_new_EO`` choose whether the old output
        removes this widget and the new output adds it.
        """
        if EO != self._output:
            if self._output is not None and notify_old_EO:
                self._output.remove_widget(self)
            if EO is not None and notify_new_EO:
                EO.add_widget(self)
        self._output = EO

    def get_EO(self):
        """Return the BLACS enum output in charge of this widget, or None."""
        return self._output

    def set_combobox_model(self, model):
        """Set the model that lists the options in the combo box."""
        self._combobox.setModel(model)

    def connect_value_change(self, func):
        """Call ``func(text)`` when the selected option's text changes."""
        self._value_changed_function = func
        self._combobox.currentTextChanged.connect(self._value_changed_function)

    def disconnect_value_change(self):
        """Stop calling the function given to ``connect_value_change``."""
        self._combobox.currentTextChanged.disconnect(self._value_changed_function)

    @property
    def selected_option(self):
        """str: the text of the selected option.

        Setting it selects the option with that text, and does nothing if there
        is none.
        """
        return str(self._combobox.currentText())

    @selected_option.setter
    def selected_option(self, option):
        if option != self.selected_option:
            model_index = self._combobox.findText(option)
            if model_index != -1:
                self._combobox.setCurrentIndex(model_index)

    @property
    def selected_index(self):
        """The data stored under the user role of the selected option.

        Setting it selects the option with that data, and raises RuntimeError if
        there is none.
        """
        return self._combobox.currentData(QtCore.Qt.ItemDataRole.UserRole)

    @selected_index.setter
    def selected_index(self, index):
        if index != self.selected_index:
            model_index = self._combobox.findData(
                index, QtCore.Qt.ItemDataRole.UserRole
            )
            if model_index != -1:
                self._combobox.setCurrentIndex(model_index)
            else:
                raise RuntimeError(f'Index {index} not found!')

    def block_combobox_signals(self):
        """Block the combo box's signals, returning whether they were blocked."""
        return self._combobox.blockSignals(True)

    def unblock_combobox_signals(self):
        """Unblock the combo box's signals, returning whether they were blocked."""
        return self._combobox.blockSignals(False)
