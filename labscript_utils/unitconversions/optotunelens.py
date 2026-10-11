#####################################################################
#                                                                   #
# optotunelens.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from numpy import exp, abs
from scipy.special import lambertw
from .UnitConversionBase import *


class OptotuneLens(UnitConversion):
    """Conversion from volts to the current and position of an Optotune lens.

    The 'distance' unit is the lens position, fitted as
    ``Pos(I) = a*exp(b*I) + c*I - a``, which is zero at zero current. Converting
    volts to 'distance' limits the current to the range 0 to ``I_Max``.

    Parameters
    ----------
    calibration_parameters : dict
        Missing keys are filled in place with their defaults.

        - ``'current_cal'``: amps per volt (default 0.05).
        - ``'I_Max'``: largest current used for 'distance', in amps (default 0.3).
        - ``'a'``, ``'b'``, ``'c'``: coefficients of the position fit (default 0).
    """

    base_unit = 'V'
    derived_units = ['distance', 'I']

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters

        self.parameters.setdefault('current_cal', 0.05)
        self.parameters.setdefault('I_Max', 0.3)

        self.parameters.setdefault('a', 0)
        self.parameters.setdefault('b', 0)
        self.parameters.setdefault('c', 0)

        super().__init__(self.parameters)

    def distance_to_base(self, percentage):
        # The inverse function is
        # I = 1/(b*c) * (-c*W((a*b/c)*exp((b/c)*(P+a))) + b*P + b*a)
        # where P is the position and W is the product log (Lambert W) function.
        amps = 1.0 / (self.parameters['b'] * self.parameters['c']) * (
            -self.parameters['c'] * lambertw(
                (self.parameters['a'] * self.parameters['b'] / self.parameters['c'])
                * exp((self.parameters['b'] / self.parameters['c'])
                      * (percentage + self.parameters['a']))
            )
            + self.parameters['b'] * percentage
            + self.parameters['b'] * self.parameters['a']
        )

        volts = amps / self.parameters['current_cal']
        return (volts > 0) * abs(volts)

    def distance_from_base(self, volts):
        amps = max(min(self.parameters['current_cal'] * volts, self.parameters['I_Max']), 0)

        percentage = (self.parameters['a'] * exp(self.parameters['b'] * amps)
                      + self.parameters['c'] * amps - self.parameters['a'])

        return percentage

    def I_to_base(self, current):
        return current / self.parameters['current_cal']

    def I_from_base(self, volts):
        return volts * self.parameters['current_cal']
