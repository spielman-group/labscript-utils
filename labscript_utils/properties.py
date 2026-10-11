import json
from base64 import b64encode, b64decode
from collections.abc import Iterable, Mapping
import numpy as np


JSON_IDENTIFIER = 'Content-Type: application/json '
BASE64_IDENTIFIER = 'Content-Transfer-Encoding: base64 '

VALID_PROPERTY_LOCATIONS = {
    "connection_table_properties",
    "device_properties",
    "unit_conversion_parameters"
    }


def _check_dicts(o):
    if isinstance(o, Mapping):
        if not all(isinstance(k, (str, bytes)) for k in o.keys()):
            raise TypeError("Cannot JSON encode dictionary with non-string keys")
        for item in o.values():
            _check_dicts(item)
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        for item in o:
            _check_dicts(item)


def _encode_bytestrings(o):
    """Encode all bytestring values (not keys) to base64 with a prefix"""
    if isinstance(o, Mapping):
        return {key: _encode_bytestrings(value) for key, value in o.items()}
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        return list([_encode_bytestrings(value) for value in o])
    elif isinstance(o, bytes):
        return BASE64_IDENTIFIER + str(b64encode(o).decode())
    else:
        return o


def _decode_bytestrings(o):
    """Decode all base64-encoded values (not keys) to bytestrings"""
    if isinstance(o, Mapping):
        return {key: _decode_bytestrings(value) for key, value in o.items()}
    elif isinstance(o, Iterable) and not isinstance(o, (str, bytes)):
        return list([_decode_bytestrings(value) for value in o])
    elif isinstance(o, str) and o.startswith(BASE64_IDENTIFIER):
        return b64decode(o[len(BASE64_IDENTIFIER):])
    else:
        return o


def is_json(value):
    """Return whether a str or bytes value is a string made by `serialise`."""
    if isinstance(value, bytes):
        return value[:len(JSON_IDENTIFIER)] == JSON_IDENTIFIER.encode('utf8')
    elif isinstance(value, str):
        return value.startswith(JSON_IDENTIFIER)
    return False


def _default(o):
    # Workaround for https://bugs.python.org/issue24313
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError


def serialise(value):
    """Encode a value as a string of JSON, prefixed to identify it as such.

    Bytestring values, but not dictionary keys, are encoded to base64 with a
    prefix, and numpy integers, floats and bools become Python ones.

    Parameters
    ----------
    value
        The value to encode, which may be nested in dicts and iterables.
        Iterables other than dicts, strings and bytes are encoded as lists.

    Returns
    -------
    str

    Raises
    ------
    TypeError
        If a dictionary has non-string keys, or a value cannot be encoded.
    """
    _check_dicts(value)
    value = _encode_bytestrings(value)
    json_string = json.dumps(value, default=_default)
    return JSON_IDENTIFIER + json_string


def deserialise(value):
    """Decode a string made by `serialise`, restoring bytestring values.

    Parameters
    ----------
    value : str or bytes
        A string for which `is_json` is true.
    """
    assert is_json(value)
    return _decode_bytestrings(json.loads(value[len(JSON_IDENTIFIER):]))


def set_attributes(group, attributes):
    """Add attributes to an HDF5 group.

    Parameters
    ----------
    group : h5py.Group
        The group to add attributes to.
    attributes : dict
        Attribute names and values. Values with no native HDF5 datatype, and
        None, are serialised with `serialise`.
    """
    for key, val in attributes.items():
        try:
            # Workaround for h5py not supporting None but not raising a TypeError:
            if val is None:
                raise TypeError('has no native HDF5 equivalent')
            group.attrs[key] = val
        except TypeError as e:
            # If type not supported by HDF5, store as JSON
            if 'has no native HDF5 equivalent' in str(e):
                json_string = serialise(val)
                group.attrs[key] = json_string
            else:
                raise


def get_attributes(group):
    """Return the attributes of an HDF5 group as a dict.

    Attributes serialised as JSON by `set_attributes` are deserialised.
    """
    return {k: deserialise(v) if is_json(v) else v for k, v in group.attrs.items()}


def get_attribute(group, name):
    """Return one attribute of an HDF5 group, deserialising it if it is JSON."""
    value = group.attrs[name]
    if is_json(value):
        return deserialise(value)
    return value


def set_device_properties(h5_file, device_name, properties):
    """Add attributes to a device's group, ``devices/<device_name>``, in a shot file.

    Parameters
    ----------
    h5_file : h5py.File
        The shot file, open for writing.
    device_name : str
        The name of the device.
    properties : dict
        The attributes to add, as for `set_attributes`.
    """
    set_attributes(h5_file['devices/' + device_name], properties)


_CONNECTION_TABLE_COLUMNS = {
    'connection_table_properties': 'properties',
    'unit_conversion_parameters': 'unit conversion params',
}


def get(h5_file, device_name, location):
    """Return a device's properties from a shot file.

    Parameters
    ----------
    h5_file : h5py.File
        The shot file.
    device_name : str
        The name of the device.
    location : str
        One of the names in ``VALID_PROPERTY_LOCATIONS``. ``'device_properties'``
        reads the attributes of the device's group in ``devices``.
        ``'connection_table_properties'`` and ``'unit_conversion_parameters'``
        read the device's row of the connection table.

    Returns
    -------
    dict

    Raises
    ------
    ValueError
        If `location` is not valid.
    """
    if location == 'device_properties':
        return get_attributes(h5_file['devices/' + device_name])
    if location in _CONNECTION_TABLE_COLUMNS:
        dataset = h5_file['connection table']
        row = dataset[dataset['name'] == device_name.encode('utf8')][0]
        return deserialise(row[_CONNECTION_TABLE_COLUMNS[location]])
    raise ValueError(f'location must be one of {VALID_PROPERTY_LOCATIONS}')
