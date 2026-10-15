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
# The save-data keys that geometry_save_data() always writes.
_WINDOW_KEYS = ('window_size', 'window_pos', 'screen_geometry')


class LabscriptGuiApplication(LabscriptApplication):
    """A labscript application whose main window is ``self.ui``.

    A subclass defines ``get_save_data()`` and ``load_configuration(filename)``,
    and sets ``last_save_config_file`` and ``last_save_data`` to ``None`` before
    the first save or load. It connects the actions of its configuration menu to
    the ``on_*_triggered`` handlers. ``config_description`` says what its
    configuration holds, for the prompt that offers to save unsaved changes
    before a load or on quitting. ``splitters`` names the main window's
    splitters, attributes of ``self.ui``: ``geometry_save_data()`` saves their
    sizes with the window's, ``restore_geometry()`` restores them, and quitting
    saves a change only to these without asking. ``load_configuration()`` ends
    with ``configuration_loaded()``.
    """

    config_description = 'GUI state'
    splitters = ()

    @inmain_decorator()
    def error_dialog(self, message):
        """Warn the user, from any thread."""
        QtWidgets.QMessageBox.warning(self.ui, self.app_name, message)

    @inmain_decorator()
    def question_dialog(self, message):
        """Ask the user a Yes/No question, from any thread.

        Returns
        -------
        bool
            True if the user answers Yes.
        """
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

    def offer_to_save_changes(self, title, quitting=False):
        """Offer to save the configuration if it has changed since the last save.

        Parameters
        ----------
        title : str
            The title of the prompt.
        quitting : bool
            If true, a change only to the window's geometry is saved without asking.

        Returns
        -------
        bool
            False if the user cancels.
        """
        save_data = self.get_save_data()
        if self.last_save_data is None or save_data == self.last_save_data:
            return True
        changed = {
            key for key in save_data if save_data[key] != self.last_save_data.get(key)
        }
        if quitting and changed <= {*_WINDOW_KEYS, *self.splitters}:
            self.save_configuration(self.last_save_config_file)
            return True
        message = (
            f'Current configuration ({self.config_description}) has changed: '
            f"save config file '{self.last_save_config_file}'?"
        )
        reply = QtWidgets.QMessageBox.question(
            self.ui, title, message, _Button.Yes | _Button.No | _Button.Cancel
        )
        if reply == _Button.Cancel:
            return False
        if reply == _Button.Yes:
            self.save_configuration(self.last_save_config_file)
        return True

    def geometry_save_data(self):
        """Return the main window's size and position, its splitters' sizes and the
        screens' geometry, as part of ``get_save_data()``."""
        size, pos = self.ui.size(), self.ui.pos()
        save_data = {
            'window_size': (size.width(), size.height()),
            'window_pos': (pos.x(), pos.y()),
            'screen_geometry': _screen_geometry(),
        }
        for name in self.splitters:
            save_data[name] = getattr(self.ui, name).sizes()
        return save_data

    def restore_geometry(self, save_data):
        """Restore what ``geometry_save_data()`` put in ``save_data``.

        Nothing is restored once the screens have changed, so that the window is
        not placed off them, nor its splitters sized for another window.
        """
        saved_screens = save_data.get('screen_geometry')
        if saved_screens is None or [tuple(s) for s in saved_screens] != _screen_geometry():
            return
        if 'window_size' in save_data:
            self.ui.resize(*save_data['window_size'])
        if 'window_pos' in save_data:
            self.ui.move(*save_data['window_pos'])
        for name in self.splitters:
            if name in save_data:
                getattr(self.ui, name).setSizes(save_data[name])

    def configuration_loaded(self, save_target):
        """Make the configuration just loaded the saved one, kept in ``save_target``.

        The Save item names the file, Save as and Revert are enabled, and the title
        shows it.
        """
        self.last_save_config_file = save_target
        self.last_save_data = self.get_save_data()
        self.ui.actionSave_configuration.setText(f'Save configuration {save_target}')
        self.ui.actionSave_configuration_as.setEnabled(True)
        self.ui.actionRevert_configuration.setEnabled(True)
        self.set_config_window_title(save_target)

    def on_load_configuration_triggered(self):
        if not self.offer_to_save_changes('Load configuration'):
            return

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


def _screen_geometry():
    return [
        (geometry.x(), geometry.y(), geometry.width(), geometry.height())
        for geometry in (screen.geometry() for screen in QtWidgets.QApplication.screens())
    ]


def exec_qapplication(qapplication):
    """Run the event loop until it ends, or until Ctrl-C in the terminal."""
    # Python runs signal handlers, Ctrl-C's or zprocess's SIGTERM, only when the
    # interpreter runs, which the timer makes happen every 500 ms.
    timer = QtCore.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)
    signal.signal(signal.SIGINT, lambda *args: qapplication.exit())
    return qapplication.exec()
