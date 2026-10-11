#####################################################################
#                                                                   #
# detuning.py                                                       #
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


class detuning(UnitConversion):
    """Laser detuning set by an AOM, whose frequency in Hz is the base unit.

    'MHz' is the AOM frequency, 'd_MHz' the detuning in MHz, and 'linewidths' the
    detuning in natural linewidths.

    Parameters
    ----------
    calibration_parameters : dict
        Missing keys are filled in place with their defaults.

        - ``'pass'``: single (1) or double (2) pass; a negative value flips the sign of
          the shift (default 1).
        - ``'detuning_0'``: detuning of the input light, in MHz (default 0).
        - ``'gamma'``: natural linewidth, in MHz (default 6.065).
        - ``'aom_f0'``: AOM frequency at resonance, in MHz. When it is false the
          detuning is measured from ``'detuning_0'`` instead (default False).
    """

    base_unit = 'Hz'
    derived_units = ['MHz', 'd_MHz', 'linewidths']

    def __init__(self, calibration_parameters=None):
        self.parameters = calibration_parameters

        self.parameters.setdefault('pass', 1)
        self.parameters.setdefault('detuning_0', 0)
        self.parameters.setdefault('gamma', 6.065)
        self.parameters.setdefault('aom_f0', False)

        super().__init__(self.parameters)

    def MHz_to_base(self, aom_frequency_MHz):
        return 1e6*aom_frequency_MHz

    def MHz_from_base(self, aom_frequency):
        return 1e-6*aom_frequency

    def d_MHz_to_base(self, detuning_MHz):
        if not self.parameters['aom_f0']:
            aom_frequency_MHz = (detuning_MHz - self.parameters['detuning_0'])/self.parameters['pass']
        else:
            aom_frequency_MHz = detuning_MHz/self.parameters['pass'] + self.parameters['aom_f0']
        return self.MHz_to_base(aom_frequency_MHz)

    def d_MHz_from_base(self, aom_frequency):
        aom_frequency_MHz = self.MHz_from_base(aom_frequency)
        if not self.parameters['aom_f0']:
            detuning_MHz = self.parameters['pass']*aom_frequency_MHz + self.parameters['detuning_0']
        else:
            detuning_MHz = self.parameters['pass']*(aom_frequency_MHz - self.parameters['aom_f0'])
        return detuning_MHz

    def linewidths_to_base(self, linewidths):
        aom_frequency = self.d_MHz_to_base(self.parameters['gamma'] * linewidths)
        return aom_frequency

    def linewidths_from_base(self, aom_frequency):
        linewidths = self.d_MHz_from_base(aom_frequency) / self.parameters['gamma']
        return linewidths
