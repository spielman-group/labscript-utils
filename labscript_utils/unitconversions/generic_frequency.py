#####################################################################
#                                                                   #
# generic_frequency.py                                              #
#                                                                   #
# Copyright 2022, Monash University and contributors                #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Generic frequency conversion"""

from .UnitConversionBase import *


class FreqConversion(UnitConversion):
    """Generic frequency conversion from a base of Hz to kHz, MHz and GHz.

    Parameters
    ----------
    calibration_parameters : dict
        Passed on to `UnitConversion`; its ``'magnitudes'`` entry is the only one used.
    """

    # Must be defined here and match the default hardware unit in the BLACS tab.
    base_unit = 'Hz'

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters
        if hasattr(self, 'derived_units'):
            self.derived_units += ['kHz', 'MHz', 'GHz']
        else:
            self.derived_units = ['kHz', 'MHz', 'GHz']
        super().__init__(self.parameters)

    def kHz_to_base(self, kHz):
        Hz = kHz*1e3
        return Hz

    def kHz_from_base(self, Hz):
        kHz = Hz*1e-3
        return kHz

    def MHz_to_base(self, MHz):
        Hz = MHz*1e6
        return Hz

    def MHz_from_base(self, Hz):
        MHz = Hz*1e-6
        return MHz

    def GHz_to_base(self, GHz):
        Hz = GHz*1e9
        return Hz

    def GHz_from_base(self, Hz):
        GHz = Hz*1e-9
        return GHz
