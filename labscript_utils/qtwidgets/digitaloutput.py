#####################################################################
#                                                                   #
# digitaloutput.py                                                  #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import sys

from qtutils.qt import QtWidgets

from .lockable import LockableOutput


class DigitalOutput(LockableOutput, QtWidgets.QPushButton):
    def __init__(self,*args,**kwargs):
        QtWidgets.QPushButton.__init__(self,*args,**kwargs)
        
        # Install the event filter that will allow us to catch right click mouse release events so we can popup a menu even when the button is disabled
        self.installEventFilter(self)
        self.setCheckable(True)
        
        # The Digital Out object that is in charge of this button
        self._output = None
    
    # Setting and getting methods for the Digitl Out object in charge of this button
    def set_DO(self,DO,notify_old_DO=True,notify_new_DO=True,inverted=False):
        # If we are setting a new DO, remove this widget from the old one (if it isn't None) and add it to the new one (if it isn't None)
        if DO != self._output:
            if self._output is not None and notify_old_DO:
                self._output.remove_widget(self)
            if DO is not None and notify_new_DO:
                DO.add_widget(self, inverted)
        # Store a reference to the digital out object
        self._output = DO
        
    def get_DO(self):
        return self._output
    
    @property
    def _lock_target(self):
        return self

    @property
    def state(self):
        return self.isChecked()
        
    @state.setter
    def state(self,state):
        # conversion to integer, then bool means we can safely pass in
        # either a string '1' or '0', True or False or 1 or 0
        self.setChecked(bool(int(state)))
    
    
class InvertedDigitalOutput(DigitalOutput):
    def set_DO(self,DO,notify_old_DO=True,notify_new_DO=True,inverted=True):
        DigitalOutput.set_DO(self, DO, notify_old_DO, notify_new_DO, inverted)

    @property
    def state(self):
        return not DigitalOutput.state.fget(self)

    @state.setter
    def state(self,state):
        DigitalOutput.state.fset(self, not state)


# A simple test!
if __name__ == '__main__':
    
    qapplication = QtWidgets.QApplication(sys.argv)
    
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(window)
    button = DigitalOutput('very very long Button')
        
    layout.addWidget(button)
    
    window.show()
    
    
    sys.exit(qapplication.exec())
    
