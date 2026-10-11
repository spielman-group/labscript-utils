#####################################################################
#                                                                   #
# quad_driver.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from .UnitConversionBase import *


class _QuadConversion(UnitConversion):
    """Quadrupole coil conversions; a subclass defines the amps conversions."""

    base_unit = 'V'
    derived_units = ['A', 'Gcm']
    default_parameters = {}

    def __init__(self, calibration_parameters=None):
        parameters = {} if calibration_parameters is None else calibration_parameters
        for name, value in self.default_parameters.items():
            parameters.setdefault(name, value)
        self.parameters = parameters
        super().__init__(parameters)

    def Gcm_to_base(self, gauss_per_cm):
        return self.A_to_base(gauss_per_cm / self.parameters['Gcm_per_A'])

    def Gcm_from_base(self, volts):
        return self.parameters['Gcm_per_A'] * self.A_from_base(volts)


class quad_driver(_QuadConversion):
    """Quadrupole coil driver, from volts to amps and gauss per cm.

    Converting amps to volts accepts an iterable, and gives 0 V below 1 mA.

    Parameters
    ----------
    calibration_parameters : dict, optional
        Missing keys are filled in place with their defaults.

        - ``'A_per_V'``: amps per volt (default 19.9757).
        - ``'Gcm_per_A'``: gauss per cm per amp (default 1.88679).
        - ``'A_offset'``: amps at zero volts (default -0.642724).
        - ``'A_min'``: lowest current the driver gives, in amps (default -0.09).
    """

    default_parameters = {
        'A_per_V': 19.9757, 'Gcm_per_A': 1.88679, 'A_offset': -0.642724, 'A_min': -0.09,
    }

    @vectorise
    def A_to_base(self, amps):
        v_min = ((self.parameters['A_min'] - self.parameters['A_offset'])
                 / self.parameters['A_per_V'])
        if amps < 0.001:
            volts = 0
        elif amps <= self.parameters['A_min']:
            volts = v_min
        else:
            volts = (amps - self.parameters['A_offset'])/self.parameters['A_per_V']
        return volts

    def A_from_base(self, volts):
        amps = max(volts * self.parameters['A_per_V'] + self.parameters['A_offset'],
                   self.parameters['A_min'])
        return amps
