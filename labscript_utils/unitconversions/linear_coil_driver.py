#####################################################################
#                                                                   #
# linear_coil_driver.py                                             #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import numpy as np
from .UnitConversionBase import *


class BidirectionalCoilDriver(UnitConversion):
    """Conversion from volts to amps for a coil driver with a linear current.

    The current is ``I[A] = slope * V[V] + shift``, where the voltage is first limited
    to a saturation value.

    Parameters
    ----------
    calibration_parameters : dict, optional
        Calibration parameters. Missing keys are filled in place with their defaults.

        - ``'slope'``: amps per volt (default 1).
        - ``'shift'``: amps at zero volts (default 0).
        - ``'saturation'``: voltage above which the current stops rising (default 10).
    """

    base_unit = 'V'
    derived_units = ['A']

    def __init__(self, calibration_parameters=None):
        if calibration_parameters is None:
            calibration_parameters = {}
        self.parameters = calibration_parameters

        self.parameters.setdefault('slope', 1)
        self.parameters.setdefault('shift', 0)
        self.parameters.setdefault('saturation', 10)

        super().__init__(self.parameters)

    def A_to_base(self, amps):
        volts = (amps - self.parameters['shift']) / self.parameters['slope']
        return volts

    def A_from_base(self, volts):
        volts = np.minimum(volts, self.parameters['saturation'])
        amps = self.parameters['slope'] * volts + self.parameters['shift']
        return amps


class UnidirectionalCoilDriver(BidirectionalCoilDriver):
    """Like `BidirectionalCoilDriver`, but zero for non-positive amps or volts."""

    def A_to_base(self, amps):
        return super().A_to_base(amps) * np.int16(amps > 0)

    def A_from_base(self, volts):
        return super().A_from_base(volts) * np.int16(volts > 0)
