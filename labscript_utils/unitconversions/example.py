#####################################################################
#                                                                   #
# example.py                                                        #
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

class example1(UnitConversion):
    # This must be defined outside of init, and must match the default hardware unit specified within the BLACS tab
    base_unit = 'V'
    
    # The parameters dictionary passed at instantiation is available to the conversions.
    # List "order of magnitude" prefixes (k, m, M, u, p) under its 'magnitudes' key and
    # the base class generates the prefixed conversions of each derived unit.
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.derived_units = ['A', 'Gauss']
        
        # Set default parameters if they are not speficied in calibration_parameters
        self.parameters.setdefault('a',2)
        self.parameters.setdefault('b',3)        
        
        UnitConversion.__init__(self,self.parameters)

    def A_to_base(self,amps):
        #here is the calibration code that may use self.parameters
        volts = amps/self.parameters['a']
        return volts
    def A_from_base(self,volts):
        #here is the calibration code that may use self.parameters
        amps = volts * self.parameters['a']
        return amps
    def Gauss_to_base(self,gauss):
        volts = gauss/self.parameters['b']
        return volts
    def Gauss_from_base(self,volts):
        gauss = (volts)*self.parameters['b']
        return gauss
        
class example2(UnitConversion):
    base_unit = 'MHz'
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.derived_units = ['detuned_MHz']
        
        # Set default parameters if they are not speficied in calibration_parameters
        self.parameters.setdefault('offset',32.7)      
        
        UnitConversion.__init__(self,self.parameters)

    def detuned_MHz_to_base(self,d_mhz):
        mhz = d_mhz - self.parameters['offset']
        return mhz
    def detuned_MHz_from_base(self,mhz):
        d_mhz = mhz + self.parameters['offset']
        return d_mhz

class example3(UnitConversion):
    base_unit = 'Vpp'
    
    def __init__(self,calibration_parameters = None):            
        self.parameters = calibration_parameters
        
        self.derived_units = ['W']
        
        # Set default parameters if they are not speficied in calibration_parameters
        self.parameters.setdefault('grad',2)      
        self.parameters.setdefault('int',0.05)      
        
        UnitConversion.__init__(self,self.parameters)

    def W_to_base(self,watts):
        vpp = float(watts - self.parameters['int'])/self.parameters['grad']
        return vpp
    def W_from_base(self,vpp):
        watts = self.parameters['grad']*vpp + self.parameters['int']
        return watts
