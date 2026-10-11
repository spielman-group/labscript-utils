#####################################################################
#                                                                   #
# settings.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
from qtutils.qt import QtCore, QtWidgets

import labscript_utils.h5_lock, h5py


class Settings:
    """A preferences dialog made of pages of settings, stored in an HDF5 file.

    Each page is an instance of a page class. A page class has a class attribute
    ``name`` that is unique among the pages, is constructed with its saved data (a
    dict), and provides ``create_dialog(notebook)``, returning ``(page_widget,
    icon)``, ``save()``, returning the data to store, ``get_value(name)`` and
    ``close()``.

    Parameters
    ----------
    storage : str, optional
        How the settings are stored. Only 'hdf5' is supported.
    file : str
        Path of the HDF5 file whose ``preferences`` group holds the settings.

    Raises
    ------
    Exception
        If no file is given.
    """

    def __init__(self, storage='hdf5', file=None, parent=None, page_classes=[]):
        self.pages = {}
        self.instantiated_pages = {}
        self.dialog_open = False
        self.parent = parent
        self.storage = storage
        self.file = file
        self.callback_list = []

        if not self.file:
            raise Exception('You must specify a file to load/save preferences from')

        for c in page_classes:
            self.add_settings_interface(c)

    def add_settings_interface(self, setting_class):
        """Add a page, loading its saved data.

        Returns
        -------
        bool
            False if a page with the same ``name`` was already added, otherwise
            True.
        """
        if setting_class.name in self.pages:
            return False

        self.pages[setting_class.name] = setting_class(self.load(setting_class.name))
        return True

    def load(self, name):
        """Return the saved data of a page, creating its entry if there is none.

        Returns
        -------
        dict
            The saved data, or an empty dict if it could not be evaluated.
        """
        if self.storage == 'hdf5':
            with h5py.File(self.file, 'r+') as h5file:
                if 'preferences' not in h5file:
                    h5file['/'].create_group('preferences')

                group = h5file['/preferences']
                if name not in group.attrs:
                    group.attrs[name] = repr({})
                try:
                    data = eval(group.attrs[name])
                except Exception:
                    # TODO: log this properly
                    print(
                        f'Could not load settings data for {name}. It may contain data '
                        'that could not be evaluated. All settings have now been lost'
                    )
                    data = {}
            return data
        else:
            raise Exception(
                f"the Settings module cannot handle the storage type: {self.storage}"
            )

    def get_value(self, settings_class, value_name):
        """Return a value from a page's settings."""
        return self.pages[settings_class.name].get_value(value_name)

    def create_dialog(self, goto_page=None):
        """Open the preferences dialog, or switch to a page if it is already open.

        Parameters
        ----------
        goto_page : type, optional
            The page class whose page to show.
        """
        if not self.dialog_open:
            self.instantiated_pages = {}

            self.dialog = QtWidgets.QDialog(self.parent)
            self.dialog.setModal(True)
            self.dialog.accepted.connect(self.on_save)
            self.dialog.rejected.connect(self.on_cancel)
            self.dialog.setMinimumSize(800, 600)
            self.dialog.setWindowTitle("Preferences")
            # Remove the help flag next to the [X] close button
            self.dialog.setWindowFlags(
                self.dialog.windowFlags()
                & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint
            )

            layout = QtWidgets.QVBoxLayout(self.dialog)
            self.notebook = QtWidgets.QTabWidget(self.dialog)
            self.notebook.show()
            layout.addWidget(self.notebook)

            widget = QtWidgets.QWidget()
            hlayout = QtWidgets.QHBoxLayout(widget)
            button_box = QtWidgets.QDialogButtonBox()
            button_box.setStandardButtons(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
                | QtWidgets.QDialogButtonBox.StandardButton.Cancel
            )
            button_box.accepted.connect(self.dialog.accept)
            button_box.rejected.connect(self.dialog.reject)
            hlayout.addItem(
                QtWidgets.QSpacerItem(
                    0,
                    0,
                    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                    QtWidgets.QSizePolicy.Policy.Minimum,
                )
            )
            hlayout.addWidget(button_box)
            layout.addWidget(widget)

            set_page = None
            for name, c in sorted(self.pages.items()):
                page, icon = c.create_dialog(self.notebook)

                self.instantiated_pages[c.__class__] = page

                self.notebook.addTab(page, c.name)

                if goto_page and isinstance(c, goto_page):
                    set_page = page

            # Select the page after all are added, since a page may insert itself out
            # of alphabetical order, such as first.
            if set_page:
                self.notebook.tabBar().setCurrentIndex(self.notebook.indexOf(set_page))

            self.dialog.show()
            self.dialog_open = True
        else:
            if goto_page and goto_page in self.instantiated_pages:
                self.notebook.tabBar().setCurrentIndex(
                    self.notebook.indexOf(self.instantiated_pages[goto_page])
                )

    def register_callback(self, callback):
        """Register a function to call, without arguments, after settings are saved."""
        self.callback_list.append(callback)

    def on_save(self, *args, **kwargs):
        """Save every page's settings, call the callbacks and close the dialog."""
        if self.storage == 'hdf5':
            with h5py.File(self.file, 'r+') as h5file:
                group = h5file['/preferences']
                for page in self.pages.values():
                    group.attrs[page.__class__.name] = repr(page.save())

        for callback in self.callback_list:
            callback()

        self.close()

    def on_cancel(self, *args, **kwargs):
        """Close the dialog without saving."""
        self.close()

    def close(self, *args, **kwargs):
        """Close every page and the dialog, if the dialog is open."""
        if self.dialog_open:
            for page in self.pages.values():
                page.close()
            self.dialog_open = False
            self.dialog.deleteLater()
            self.dialog = None
