#####################################################################
#                                                                   #
# /connections.py                                                   #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of labscript_utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

import labscript_utils.h5_lock, h5py
import labscript_utils.properties
import logging
import labscript_utils.excepthook
import numpy as np
import copy
import ast
import sys
from zprocess import raise_exception_in_thread
from labscript_utils import ensure_str


class ConnectionTable:
    """The connection table stored in an HDF5 file.

    Parameters
    ----------
    h5file : str or pathlib.Path
        File holding the 'connection table' dataset.
    logging_prefix : str, optional
        If given, log to the logger ``<logging_prefix>.ConnectionTable``.
    exceptions_in_thread : bool, optional
        If True, a failure to read or parse the table is raised in a new
        thread with `zprocess.raise_exception_in_thread` instead of being
        raised from the constructor.

    Attributes
    ----------
    filepath : str or pathlib.Path
        The `h5file` argument.
    raw_table : numpy.ndarray
        The connection table dataset, one row per device.
    table : dict
        `Connection` objects keyed by device name.
    toplevel_children : dict
        The `Connection` objects with no parent port, keyed by device name.
    master_pseudoclock : str or None
        Name of the master pseudoclock, if the file records one.
    """

    def __init__(self, h5file, logging_prefix=None, exceptions_in_thread=False):
        self.filepath = h5file
        self.logger = None
        if logging_prefix is not None:
            self.logger = logging.getLogger(f'{logging_prefix}.ConnectionTable')
            self.logger.debug(f'Parsing connection table from {h5file}')

        self.toplevel_children = {}
        self.table = {}
        self.master_pseudoclock = None
        self.raw_table = np.empty(0)

        try:
            with h5py.File(h5file,'r') as hdf5_file:
                try:
                    dataset = hdf5_file['connection table']
                except Exception:
                    msg = f'could not open connection table dataset in {h5file}'
                    if self.logger: self.logger.error(msg)
                    if exceptions_in_thread:
                        raise_exception_in_thread(sys.exc_info())
                    else:
                        raise
                    return

                self.raw_table = dataset[:]
                try:
                    self.master_pseudoclock = ensure_str(dataset.attrs['master_pseudoclock'])
                except KeyError:
                    pass

                try:
                    all_connections = [Connection(raw_row) for raw_row in self.raw_table]
                    self.table = {connection.name: connection for connection in all_connections}
                    for name, connection in self.table.items():
                        connection._populate_relatives(self.table)
                        if connection.parent_port is None:
                            self.toplevel_children[name] = connection
                except Exception:
                    msg = f'Could not parse connection table in {h5file}'
                    if self.logger: self.logger.error(msg)
                    if exceptions_in_thread:
                        raise_exception_in_thread(sys.exc_info())
                    else:
                        raise

        except Exception:
            msg = f'Could not open connection table file {h5file}'
            if self.logger: self.logger.exception(msg)
            if exceptions_in_thread:
                raise_exception_in_thread(sys.exc_info())
            else:
                raise

    def compare_to(self, other):
        """Check that this table contains every device in another table.

        Devices that exist only in this table do not count as a mismatch.

        Parameters
        ----------
        other : ConnectionTable
            The table whose devices must all be present here, with the same
            class, parent port, unit conversion, BLACS connection and
            properties.

        Returns
        -------
        tuple of (bool, dict)
            Whether the tables are compatible, and a dict describing the
            differences, which is empty when they are. Its keys are
            ``'children_missing'`` (devices of `other` absent here, name to
            True), ``'children'`` (name to the error dict from
            `Connection.compare_to`) and, if `other` is not a
            `ConnectionTable`, ``'error'``.
        """
        if not isinstance(other, ConnectionTable):
            return False, {"error": "The connection table passed in is not a valid connection table"}
        error = {}
        # Check if top level children in other table are a subset of self.
        for name, connection in other.toplevel_children.items():
            if not name in self.toplevel_children:
                if self.logger: self.logger.error(f'missing: {name} ')
                if "children_missing" not in error:
                    error["children_missing"] = {}
                error["children_missing"][name] = True
            else:
                # for each top level child in other, check if children of that object are also children of the child in self.
                result, child_error = self.toplevel_children[name].compare_to(connection)
                if not result:
                    if self.logger: self.logger.error('Connection table mismatch')
                    if "children" not in error:
                        error["children"] = {}
                    error["children"][name] = child_error

        if error != {}:
            return False,error
        else:
            return True,error

    def print_details(self):
        """Print the device tree, children indented below their parent."""
        for key, value in self.toplevel_children.items():
            print(key)
            value.print_details('  ')

    def get_attached_devices(self):
        """Find the devices that are connected to BLACS.

        Returns
        -------
        dict
            Device instance name to labscript class name, for every device
            whose 'BLACS_connection' is non-empty.
        """
        attached_devices = {}
        for name, device in self.table.items():
            if device.BLACS_connection:
                # The device is connected to BLACS. Save its name and class:
                attached_devices[name] = device.device_class
        return attached_devices

    def find_child(self, parent_name, parent_port):
        """Find the device connected to a given port of a given device.

        Parameters
        ----------
        parent_name : str
            Name of the parent device, e.g. ``'pulseblaster_0'``.
        parent_port : str
            Parent port the child is connected through, e.g. ``'dds 0'``.

        Returns
        -------
        Connection or None
            The matching device, or None if there is none.
        """
        for name, connection in self.table.items():
            if (connection.parent_name == parent_name
                    and connection.parent_port == parent_port):
                return connection
        return None

    def find_by_name(self,name):
        """Find a device by name, searching the whole device tree.

        Returns
        -------
        Connection or None
            The device called `name`, or None if there is none.
        """
        name = ensure_str(name)
        for device_name, connection in self.toplevel_children.items():
            if device_name == name:
                return connection
            else:
                result = connection.find_by_name(name)
                if result is not None:
                    return result
        return None

    def remove_device(self, device_name):
        """Remove a device from the table, but keep it in `raw_table`.

        This lets comparisons of connection tables fail for tables with broken
        devices.
        """
        if device_name in self.toplevel_children:
            del self.toplevel_children[device_name]
        if device_name == self.master_pseudoclock:
            self.master_pseudoclock = None
        del self.table[device_name]


class Connection:
    """A row of the connection table.

    The row's fields are deserialised and presented as attributes, with
    defaults supplied for fields that older HDF5 files lack.

    Parameters
    ----------
    raw_row : numpy.void
        One row of the 'connection table' dataset.

    Attributes
    ----------
    name, device_class, parent_name, parent_port, unit_conversion_class,
    BLACS_connection : str or None
        The row's 'name', 'class', 'parent', 'parent port', 'unit conversion
        class' and 'BLACS_connection' fields. `parent_port` and
        `unit_conversion_class` are None if the row has none.
    unit_conversion_params, properties : dict
        Copies of the row's 'unit conversion params' and 'properties' fields.
    child_list : dict
        The `Connection` objects of child devices, keyed by name. Filled in
        by the `ConnectionTable`.
    parent : Connection or None
        The parent device. Filled in by the `ConnectionTable`.
    """
    _defaults = {'unit conversion class': None,
                'unit conversion params': {},
                'BLACS_connection': "",
                'properties': {}}

    def __init__(self, raw_row):

        # Populate a dict with the defaults:
        self._rowdict = self._defaults.copy()

        # Put the given values in, overwriting the defaults if applicable:
        deserialised_items = {ensure_str(name): self._deserialise(name, value)
                              for name, value in zip(raw_row.dtype.names, raw_row)}

        self._rowdict.update(deserialised_items)

        # Populate attributes:
        self.name = self._rowdict['name']
        self.device_class = self._rowdict['class']
        self.parent_name = self._rowdict['parent']
        self.parent_port = self._rowdict['parent port']
        self.unit_conversion_class = self._rowdict['unit conversion class']
        self._unit_conversion_params = self._rowdict['unit conversion params']
        self.BLACS_connection = self._rowdict['BLACS_connection']
        self._properties = self._rowdict['properties']

        # To be populated by self._populate_relatives:
        self.child_list = {}
        self.parent = None

    def _deserialise(self, name, value):
        if name in ['parent port', 'unit conversion class']:
            # If no unit conversion class, or parent port, set to the object
            # None, otherwise leave as the parent port string or unit
            # conversion class name as a (unicode) string
            if ensure_str(value) == 'None':
                return None
        elif name in ['unit conversion params', 'properties']:
            # deserialise a dict that is stored as a string. In older
            # labscript these were repr() of the dict, in newer they are
            # stored as JSON.
            if labscript_utils.properties.is_json(value):
                return labscript_utils.properties.deserialise(value)
            else:
                return ast.literal_eval(ensure_str(value))
        return ensure_str(value)

    def _populate_relatives(self, table):
        for name, connection in table.items():
            if connection.parent_name == self.name:
                self.child_list[connection.name] = connection
            if name == self.parent_name:
                self.parent = connection

    def __eq__(self, other):
        return self._rowdict == other._rowdict

    def __ne__(self, other):
        return self._rowdict != other._rowdict

    @property
    def unit_conversion_params(self):
        # Return a copy so calling code can't modify our instance attribute
        return copy.deepcopy(self._unit_conversion_params)

    @property
    def properties(self):
        # Return a copy so calling code can't modify our instance attribute
        return copy.deepcopy(self._properties)

    def compare_to(self, other_connection):
        """Check that another connection's device and its children exist here.

        Compares the name, class, parent port, unit conversion, BLACS
        connection and properties, then recurses into the children of
        `other_connection`. Children present only here are ignored.

        Parameters
        ----------
        other_connection : Connection
            The device to compare against.

        Returns
        -------
        tuple of (bool, dict)
            Whether the devices match, and a dict describing the differences,
            which is empty when they do. Its keys are the attribute names that
            differ (value True), ``'children_missing'`` (children of
            `other_connection` absent here, name to True) and ``'children'``
            (name to the error dict of that child).
        """
        if not isinstance(other_connection,Connection):
            return False,{"error":"Internal Error. Connection Table object is corrupted."}

        error = {}
        # Compare all parameters between this connection, and other connection
        if self.name != other_connection.name:
            error["name"] = True
        if self.device_class != other_connection.device_class:
            error["device_class"] = True
        if self.parent_port != other_connection.parent_port:
            error["parent_port"] = True
        if self.unit_conversion_class != other_connection.unit_conversion_class:
            error["unit_conversion_class"] = True
        if self.unit_conversion_params != other_connection.unit_conversion_params:
            error["unit_conversion_params"] = True
        if self.BLACS_connection != other_connection.BLACS_connection:
            error["BLACS_connection"] = True
        if self.properties != other_connection.properties:
            error["properties"] = True

        # for each child in other_connection, check that the child also exists here
        for name, connection in other_connection.child_list.items():
            if not name in self.child_list:
                error.setdefault("children_missing",{})
                error["children_missing"][name] = True

            else:
                # call compare_to on child so that we can check it's children!
                result, child_error = self.child_list[name].compare_to(connection)
                if not result:
                    error.setdefault("children",{})
                    error["children"][name] = child_error

        if error != {}:
            return False, error
        else:
            return True, error

    def print_details(self,indent):
        """Print the names of all descendants, each level indented further.

        Parameters
        ----------
        indent : str
            Prefix for the names of the children.
        """
        for name, child in self.child_list.items():
            print(indent + name)
            child.print_details(indent + '  ')

    def find_child(self, parent_name, parent_port):
        """Find a descendant connected to a given port of a given device.

        Parameters
        ----------
        parent_name : str
            Name of the parent device.
        parent_port : str
            Parent port the child is connected through.

        Returns
        -------
        Connection or None
            The matching descendant, or None if there is none.
        """
        for name, connection in self.child_list.items():
            if connection.parent_name == parent_name and connection.parent_port == parent_port:
                return connection

        # This is done separately to the above iteration for speed.
        # We search for all children first, before going down another layer.
        for name, connection in self.child_list.items():
            result = connection.find_child(parent_name, parent_port)
            if result is not None:
                return result

        return None

    def find_by_name(self, name):
        """Find a descendant by name.

        Returns
        -------
        Connection or None
            The descendant called `name`, or None if there is none.
        """
        name = ensure_str(name)
        for device_name, connection in self.child_list.items():
            if device_name == name:
                return connection
            else:
                result = connection.find_by_name(name)
                if result is not None:
                    return result
        return None
