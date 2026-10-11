#####################################################################
#                                                                   #
# /labscript_utils/qtwidgets/application.py                         #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import signal

from qtutils import inmain_decorator
from qtutils.qt import QtCore, QtWidgets

from labscript_utils.labconfig import LabscriptApplication
import labscript_utils.qtwidgets.file_dialogs as file_dialogs

_Button = QtWidgets.QMessageBox.StandardButton


class LabscriptGuiApplication(LabscriptApplication):
    """A labscript application whose main window is ``self.ui``.

    Adds the handlers of the configuration menu, and error and question dialogs
    that belong to the window.

    Notes
    -----
    A subclass defines ``get_save_data()`` and ``load_configuration(filename)``,
    and sets ``last_save_config_file`` and ``last_save_data`` to ``None`` before
    the first save or load. It connects the actions of its configuration menu to
    the ``on_*_triggered`` handlers. ``config_description`` says what its
    configuration holds, for the prompt that offers to save unsaved changes
    before a load.
    """

    config_description = 'GUI state'

    @inmain_decorator()
    def error_dialog(self, message):
        """Warn the user with ``message``, from any thread."""
        QtWidgets.QMessageBox.warning(self.ui, self.app_name, message)

    @inmain_decorator()
    def question_dialog(self, message):
        """Ask the user a Yes/No ``message`` from any thread, and return the answer."""
        reply = QtWidgets.QMessageBox.question(
            self.ui, self.app_name, message, _Button.Yes | _Button.No
        )
        return reply == _Button.Yes

    def on_save_configuration_triggered(self):
        if self.last_save_config_file is None:
            self.on_save_configuration_as_triggered()
            self.ui.actionSave_configuration_as.setEnabled(True)
            self.ui.actionRevert_configuration.setEnabled(True)
        else:
            self.save_configuration(self.last_save_config_file)

    def on_revert_configuration_triggered(self):
        save_data = self.get_save_data()
        if self.last_save_data is not None and save_data != self.last_save_data:
            message = (
                'Revert configuration to the last saved state in '
                f"'{self.last_save_config_file}'?"
            )
            reply = QtWidgets.QMessageBox.question(
                self.ui, 'Load configuration', message, _Button.Yes | _Button.Cancel
            )
            if reply == _Button.Yes:
                self.load_configuration(self.last_save_config_file)
        else:
            self.error_dialog('no changes to revert')

    def on_save_configuration_as_triggered(self):
        if self.last_save_config_file is not None:
            default = self.last_save_config_file
        else:
            default = self.get_default_config_file(ensure_directory=True)
        save_file = file_dialogs.save_file(
            self.ui,
            f'Select file to save current {self.app_name} configuration',
            default,
            'Config files (*.toml)',
        )
        if save_file is None:
            return
        self.save_configuration(save_file)
        self.ui.actionSave_configuration.setText(
            f'Save configuration {self.last_save_config_file}'
        )

    def on_load_configuration_triggered(self):
        save_data = self.get_save_data()
        if self.last_save_data is not None and save_data != self.last_save_data:
            message = (
                f'Current configuration ({self.config_description}) has changed: '
                f"save config file '{self.last_save_config_file}'?"
            )
            reply = QtWidgets.QMessageBox.question(
                self.ui,
                'Load configuration',
                message,
                _Button.Yes | _Button.No | _Button.Cancel,
            )
            if reply == _Button.Cancel:
                return
            if reply == _Button.Yes:
                self.save_configuration(self.last_save_config_file)

        if self.last_save_config_file is not None:
            default = self.last_save_config_file
        else:
            default = self.get_default_config_file()

        # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
        file = file_dialogs.open_file(
            self.ui,
            f'Select {self.app_name} configuration file to load',
            default,
            'Config files (*.toml *.ini)',
        )
        if file is not None:
            self.load_configuration(file)


def exec_qapplication(qapplication):
    """Run the event loop until it ends, or until Ctrl-C in the terminal.

    Parameters
    ----------
    qapplication : QApplication
        The application whose event loop runs.

    Returns
    -------
    int
        The exit code of the event loop.
    """
    # Python runs signal handlers, Ctrl-C's or zprocess's SIGTERM, only when the
    # interpreter runs, which the timer makes happen every 500 ms.
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    signal.signal(signal.SIGINT, lambda *args: qapplication.exit())
    return qapplication.exec()
