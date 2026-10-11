#####################################################################
#                                                                   #
# quad_monitor.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from .quad_driver import _QuadConversion


class quad_monitor(_QuadConversion):
    """Quadrupole coil current monitor, from volts to amps and gauss per cm.

    Parameters
    ----------
    calibration_parameters : dict, optional
        Calibration parameters. Missing keys are filled in place with their defaults.

        - ``'A_per_V'``: amps per volt (default 20.032).
        - ``'Gcm_per_A'``: gauss per cm per amp (default 1.88679).
        - ``'A_offset'``: amps at zero volts (default 0.0968 - 0.14).
    """

    default_parameters = {
        'A_per_V': 20.032, 'Gcm_per_A': 1.88679, 'A_offset': 0.0968 - 0.14,
    }

    def A_to_base(self, amps):
        volts = (amps - self.parameters['A_offset'])/self.parameters['A_per_V']
        return volts

    def A_from_base(self, volts):
        amps = volts * self.parameters['A_per_V'] + self.parameters['A_offset']
        return amps
