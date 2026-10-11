#####################################################################
#                                                                   #
# NovaTechDDS9m.py                                                  #
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


class NovaTechDDS9mFreqConversion(UnitConversion):
    """Frequency conversion of a NovaTech DDS9m channel, from Hz to MHz.

    Parameters
    ----------
    calibration_parameters : dict
        Only the ``'magnitudes'`` entry is used (see `UnitConversion`).
    """

    # Must be defined outside of __init__, and must match the default hardware unit
    # specified within the BLACS tab.
    base_unit = 'Hz'

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters
        if hasattr(self, 'derived_units'):
            self.derived_units.append('MHz')
        else:
            self.derived_units = ['MHz']
        super().__init__(self.parameters)

    def MHz_to_base(self, MHz):
        Hz = MHz*10.0**6
        return Hz

    def MHz_from_base(self, Hz):
        MHz = Hz/10.0**6
        return MHz


class NovaTechDDS9mAmpConversion(UnitConversion):
    """Amplitude conversion of a NovaTech DDS9m channel, from 'Arb' to hardware units.

    The 'hardware' unit is the DDS's integer amplitude step, 1023 being full scale, 1 'Arb'.

    Parameters
    ----------
    calibration_parameters : dict
        Only the ``'magnitudes'`` entry is used (see `UnitConversion`).
    """

    # Must be defined outside of __init__, and must match the default hardware unit
    # specified within the BLACS tab.
    base_unit = 'Arb'

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters

        if hasattr(self, 'derived_units'):
            self.derived_units.append('hardware')
        else:
            self.derived_units = ['hardware']

        super().__init__(self.parameters)

    def hardware_to_base(self, hardware):
        arb = hardware/1023.0
        return arb

    def hardware_from_base(self, arb):
        hardware = arb*1023.0
        return hardware
