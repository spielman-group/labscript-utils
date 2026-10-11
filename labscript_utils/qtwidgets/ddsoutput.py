#####################################################################
#                                                                   #
# ddsoutput.py                                                      #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################

from qtutils.qt import QtCore, QtWidgets

from labscript_utils.qtwidgets.analogoutput import AnalogOutput
from labscript_utils.qtwidgets.digitaloutput import DigitalOutput


class DDSOutput(QtWidgets.QWidget):
    """A framed set of widgets for one DDS output: gate, frequency, amplitude and phase.

    The sub-channels are named ``'gate'``, ``'freq'``, ``'amp'`` and ``'phase'``. The
    gate is a DigitalOutput and the others are AnalogOutputs.

    Parameters
    ----------
    hardware_name : str
        The name of the output, shown in the label with ``connection_name``.
    connection_name : str, optional
        The connection of the output, shown below ``hardware_name``.
    parent : QWidget, optional
    """

    def __init__(self, hardware_name, connection_name='-', parent=None):
        super().__init__(parent)

        self._connection_name = connection_name
        self._hardware_name = hardware_name

        label_text = self._hardware_name + '\n' + self._connection_name
        self._label = QtWidgets.QLabel(label_text)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum
        )

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.MinimumExpanding, QtWidgets.QSizePolicy.Policy.Minimum
        )

        self._widgets = {}
        self._widgets['gate'] = DigitalOutput('Enable')
        self._widgets['freq'] = AnalogOutput(
            '', display_name='<i>f&nbsp;</i>', horizontal_alignment=True
        )
        self._widgets['amp'] = AnalogOutput(
            '', display_name='<i>A</i>', horizontal_alignment=True
        )
        self._widgets['phase'] = AnalogOutput(
            '', display_name='<i>&phi;</i>', horizontal_alignment=True
        )

        # Extra layout at the top level with horizontal stretches so that our
        # widgets do not grow to take up all available horizontal space:
        self._outer_layout = QtWidgets.QHBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._frame = QtWidgets.QFrame(self)
        self._outer_layout.addStretch()
        self._outer_layout.addWidget(self._frame)
        self._outer_layout.addStretch()

        # A grid layout keeps the widgets from expanding, and the label centred
        # above them.
        self._layout = QtWidgets.QGridLayout(self._frame)
        self._layout.setVerticalSpacing(6)
        self._layout.setHorizontalSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)

        v_widget = QtWidgets.QFrame()
        v_widget.setFrameStyle(QtWidgets.QFrame.Shape.StyledPanel)
        v_layout = QtWidgets.QVBoxLayout(v_widget)
        v_layout.setContentsMargins(6, 6, 6, 6)

        # Extra widget with stretches around the enabled button so it doesn't
        # stretch out to fill all horizontal space:
        self.gate_container = QtWidgets.QWidget()
        gate_layout = QtWidgets.QHBoxLayout(self.gate_container)
        gate_layout.setContentsMargins(0, 0, 0, 0)
        gate_layout.setSpacing(0)
        gate_layout.addStretch()
        gate_layout.addWidget(self._widgets['gate'])
        gate_layout.addStretch()

        self._widgets['gate'].setToolTip("Enable")
        self._widgets['freq'].setToolTip("Frequency")
        self._widgets['amp'].setToolTip("Amplitude")
        self._widgets['phase'].setToolTip("Phase")

        v_layout.addWidget(self.gate_container)
        v_layout.addWidget(self._widgets['freq'])
        v_layout.addWidget(self._widgets['amp'])
        v_layout.addWidget(self._widgets['phase'])

        self._layout.addWidget(self._label, 0, 0)
        self._layout.addWidget(v_widget, 1, 0)
        self._layout.addItem(
            QtWidgets.QSpacerItem(
                0, 0,
                QtWidgets.QSizePolicy.Policy.Minimum,
                QtWidgets.QSizePolicy.Policy.MinimumExpanding,
            ),
            2, 0,
        )

    def get_sub_widget(self, subchnl):
        """Return the widget of a sub-channel, raising RuntimeError for any other name."""
        if subchnl in self._widgets:
            return self._widgets[subchnl]

        raise RuntimeError(
            f'The sub-channel {subchnl} must be either gate, freq, amp or phase'
        )

    def hide_sub_widget(self, subchnl):
        """Hide the widget of a sub-channel, raising RuntimeError for any other name."""
        if subchnl in self._widgets:
            if subchnl == 'gate':
                self.gate_container.hide()
            else:
                self._widgets[subchnl].hide()
            return

        raise RuntimeError(
            f'The sub-channel {subchnl} must be either gate, freq, amp or phase'
        )

    def show_sub_widget(self, subchnl):
        """Show the widget of a sub-channel, raising RuntimeError for any other name."""
        if subchnl in self._widgets:
            if subchnl == 'gate':
                self.gate_container.show()
            else:
                self._widgets[subchnl].show()
            return

        raise RuntimeError(
            f'The sub-channel {subchnl} must be either gate, freq, amp or phase'
        )
