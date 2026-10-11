#####################################################################
#                                                                   #
# enumcontrol.py                                                    #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import sys

from qtutils.qt import QtCore, QtGui, QtWidgets

from .lockable import LockableOutput


class EnumOutput(LockableOutput, QtWidgets.QWidget):
    def __init__(self, hardware_name, connection_name='-', display_name=None, horizontal_alignment=False, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        
        self._connection_name = connection_name
        self._hardware_name = hardware_name
        
        label_text = (self._hardware_name + '\n' + self._connection_name) if display_name is None else display_name
        self._label = QtWidgets.QLabel(label_text)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed,QtWidgets.QSizePolicy.Policy.Minimum)
        self._combobox = QtWidgets.QComboBox()
        self._combobox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum,QtWidgets.QSizePolicy.Policy.Minimum)
        self._lock_target = self._combobox

        self._value_changed_function = None
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,QtWidgets.QSizePolicy.Policy.Minimum)
        
        # Create widgets and layouts        
        if horizontal_alignment:
            self._layout = QtWidgets.QHBoxLayout(self)
            self._layout.addWidget(self._label)
            self._layout.addWidget(self._combobox)
            self._layout.setContentsMargins(0,0,0,0)
        else:
            self._layout = QtWidgets.QGridLayout(self)
            self._layout.setVerticalSpacing(3)
            self._layout.setHorizontalSpacing(0)
            self._layout.setContentsMargins(3,3,3,3)
            
            self._label.setSizePolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding,QtWidgets.QSizePolicy.Policy.Minimum)
            
            h_widget = QtWidgets.QWidget()            
            h_layout = QtWidgets.QHBoxLayout(h_widget)
            h_layout.setContentsMargins(0,0,0,0)
            h_layout.addWidget(self._combobox)
            
            self._layout.addWidget(self._label,0,0)
            self._layout.addWidget(h_widget,1,0)            
            self._layout.addItem(QtWidgets.QSpacerItem(0,0,QtWidgets.QSizePolicy.Policy.Minimum,QtWidgets.QSizePolicy.Policy.MinimumExpanding),2,0)
        
        # Install the event filter that will allow us to catch right click mouse release events so we can popup a menu even when the button is disabled
        self.installEventFilter(self)
        
        # The Analog Out object that is in charge of this button
        self._output = None
    
    # Setting and getting methods for the object in charge of this button
    def set_EO(self,EO,notify_old_EO=True,notify_new_EO=True):
        # If we are setting a new EO, remove this widget from the old one (if it isn't None) and add it to the new one (if it isn't None)
        if EO != self._output:
            if self._output is not None and notify_old_EO:
                self._output.remove_widget(self)
            if EO is not None and notify_new_EO:
                EO.add_widget(self)
        # Store a reference to the digital out object
        self._output = EO
        
    def get_EO(self):
        return self._output
    
    def set_combobox_model(self,model):
        self._combobox.setModel(model)

    def connect_value_change(self,func):
        self._value_changed_function = func
        self._combobox.currentTextChanged.connect(self._value_changed_function)
        
    def disconnect_value_change(self):
        self._combobox.currentTextChanged.disconnect(self._value_changed_function)
    
    @property
    def selected_option(self):
        return str(self._combobox.currentText())
    
    @selected_option.setter
    def selected_option(self,option):
        if option != self.selected_option:
            #item = self._combobox.model().findItems(option)
            model_index = self._combobox.findText(option)
            if model_index != -1:
                #model_index = self._combobox.model().indexFromItem(item[0]).row()
                self._combobox.setCurrentIndex(model_index)

    @property
    def selected_index(self):
        return self._combobox.currentData(QtCore.Qt.ItemDataRole.UserRole)

    @selected_index.setter
    def selected_index(self,index):
        if index != self.selected_index:
            model_index = self._combobox.findData(index,QtCore.Qt.ItemDataRole.UserRole)
            if model_index != -1:
                self._combobox.setCurrentIndex(model_index)
            else:
                raise RuntimeError('Index {index} not found!'.format(index=index))

    def block_combobox_signals(self):
        return self._combobox.blockSignals(True)
        
    def unblock_combobox_signals(self):
        return self._combobox.blockSignals(False)


# A simple test!
if __name__ == '__main__':
    
    qapplication = QtWidgets.QApplication(sys.argv)
    
    window = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(window)

    test_options = {'option 1':{'index':0,'tooltip':"Option 1 Description"},
                    'option 2':{'index':1,'tooltip':"Option 2 Description"},
                    'option 3':2}
    test_model = QtGui.QStandardItemModel()
    for key,val in test_options.items():
        item = QtGui.QStandardItem(key)
        if type(val) is not dict:
            item.setData(val,QtCore.Qt.ItemDataRole.UserRole)
        else:
            item.setData(val['index'],QtCore.Qt.ItemDataRole.UserRole)
            item.setData(val['tooltip'],QtCore.Qt.ItemDataRole.ToolTipRole)
        test_model.appendRow(item)
    combobox = EnumOutput('Enumerate',display_name='Test Name',
                            horizontal_alignment=True)        
    layout.addWidget(combobox)
    combobox.set_combobox_model(test_model)
    
    window.show()
    
    
    sys.exit(qapplication.exec())
    
