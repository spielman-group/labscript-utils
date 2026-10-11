#####################################################################
#                                                                   #
# aom.py                                                            #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from numpy import arccos, cos, pi
from .UnitConversionBase import *
from .NovaTechDDS9m import NovaTechDDS9mAmpConversion


class SineAom(NovaTechDDS9mAmpConversion):
    """Power calibration of an AOM whose power is very close to a sine of the drive.

    The power P in 'Power' units depends on the DDS amplitude x, in 'Arb', as
    ``P(x) = A * cos(2*pi*f * x + phase) + c``. The 'fraction' unit is the power as a
    fraction of the range from ``max(c - A, 0)`` to ``A + c``. The 'hardware' unit is
    inherited from `NovaTechDDS9mAmpConversion`.

    Parameters
    ----------
    calibration_parameters : dict
        Calibration parameters. Missing keys are filled in place with their defaults.

        - ``'A'``: amplitude of the sine (default 1.969).
        - ``'f'``: frequency of the sine, per 'Arb' (default 0.527).
        - ``'phase'``: phase of the sine, reduced modulo 2*pi in place (default 3.262).
        - ``'c'``: offset of the sine (default 1.901).
    """

    base_unit = "Arb"

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters
        self.derived_units = ["Power", "fraction"]
        self.parameters.setdefault('A', 1.969)
        self.parameters.setdefault('f', 0.527)
        self.parameters.setdefault('phase', 3.262)
        self.parameters.setdefault('c', 1.901)

        self.parameters['phase'] = self.parameters['phase'] % (2*pi)

        super().__init__(self.parameters)

    def Power_to_base(self, power):
        a = self.parameters["A"]
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        c = self.parameters["c"]
        if ((phase / pi) % 2) == 0:
            phi = (arccos((power - c) / a) - phase) % (2*pi)
        else:
            phi = (2*pi - arccos((power - c) / a) - phase) % (2*pi)
        return phi / (2*pi*f)

    def Power_from_base(self, amp):
        a = self.parameters["A"]
        f = self.parameters["f"]
        phase = self.parameters["phase"]
        c = self.parameters["c"]

        return a * cos(2*pi*f*amp + phase) + c

    def fraction_to_base(self, fraction):
        p_max = self.parameters["A"] + self.parameters["c"]
        p_min = max(self.parameters["c"] - self.parameters["A"], 0)
        power = (p_max - p_min) * fraction + p_min
        amp = self.Power_to_base(power)
        return amp

    def fraction_from_base(self, amp):
        f = self.parameters["f"]
        phase = self.parameters["phase"]

        if 2*pi*f*amp + phase > 2*pi:
            amp = (2*pi - phase) / (2*pi*f)

        power = self.Power_from_base(amp)
        p_max = self.parameters["A"] + self.parameters["c"]
        p_min = max(self.parameters["c"] - self.parameters["A"], 0)
        fraction = (power - p_min) / (p_max - p_min)
        return fraction
