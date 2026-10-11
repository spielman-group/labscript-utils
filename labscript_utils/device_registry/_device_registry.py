"""Registration and lookup of the BLACS tab and runviewer parser classes that belong to
a labscript device. Device class names must be unique, such as "PulseBlaster".

A file called 'register_classes.py', at any depth within labscript_devices or a package
named by the 'user_devices' labconfig setting, calls register_classes() with the fully
qualified names of the device's tab and parser classes, so the imports are deferred
until the classes are needed. get_BLACS_tab() and get_runviewer_parser() call
populate_registry() to run every such file.

If a device has no entry, they fall back on a module <DeviceName>.py at the top level of
labscript_devices, whose classes are decorated with @BLACS_tab or @runviewer_parser.
"""

import importlib.machinery
import os
import importlib
import warnings
import traceback
import inspect
from labscript_utils import dedent
from labscript_utils.labconfig import LabConfig
from labscript_profile.toml_config import as_config_list


__all__ = [
    'LABSCRIPT_DEVICES_DIRS',
    'labscript_device',
    'BLACS_worker',
    'BLACS_tab',
    'runviewer_parser',
    'import_class_by_fullname',
    'deprecated_import_alias',
    'get_BLACS_tab',
    'get_runviewer_parser',
    'register_classes',
]


def _get_import_paths(import_names):
    """For the given list of packages, return all folders containing their submodules.
    If the packages do not exist, ignore them."""
    paths = []
    for name in import_names:
        spec = importlib.util.find_spec(name)
        if spec is not None and spec.submodule_search_locations is not None:
            paths.extend(spec.submodule_search_locations)
    return paths


def _get_device_dirs():
    """Return the directory of labscript_devices, and the folders containing
    submodules of any packages listed in the user_devices labconfig setting"""
    try:
        user_devices = LabConfig().get('default', 'user_devices')
    except (LabConfig.NoOptionError, LabConfig.NoSectionError):
        user_devices = 'user_devices'
    # Accept a comma-separated string or a TOML array:
    user_devices = as_config_list(user_devices)
    return _get_import_paths(['labscript_devices'] + user_devices)


LABSCRIPT_DEVICES_DIRS = _get_device_dirs()


class ClassRegister:
    """A register of classes by the name of the module that defines them.

    Calling an instance on a class, as a decorator, registers the class under
    its module's name. Indexing the instance by a module name imports the module
    from labscript_devices if necessary and returns its registered class.

    Parameters
    ----------
    instancename : str
        The name of the instance in this namespace, used in error messages.
    """

    def __init__(self, instancename):
        self.registered_classes = {}
        # The name given to the instance in this namespace, so we can use it in error messages:
        self.instancename = instancename

    def __call__(self, cls):
        """Register a class under its module's name, and return it."""
        # Add an attribute to the class so it knows its own name in case
        # it needs to look up other classes in the same module:
        cls.labscript_device_class_name = cls.__module__.split('.')[-1]
        if cls.labscript_device_class_name == '__main__':
            # User is running the module as __main__. Use the filename instead:
            import __main__
            try:
                cls.labscript_device_class_name = os.path.splitext(os.path.basename(__main__.__file__))[0]
            except AttributeError:
                # Maybe they're running interactively? Or some other funky environment. Either way, we can't proceed.
                raise RuntimeError("Can't figure out what the file or module this class is being defined in. " +
                                   'If you are testing, please test from a more standard environment, such as ' +
                                   'executing a script from the command line, or if you are using an interactive session, ' +
                                   'writing your code in a separate module and importing it.')

        self.registered_classes[cls.labscript_device_class_name] = cls
        return cls

    def __getitem__(self, name):
        """Return the class registered for the module labscript_devices.<name>.

        Raises
        ------
        ImportError
            If that module cannot be imported.
        ValueError
            If the module registers no class with this register.
        """
        try:
            # Ensure the module's code has run (this does not re-import it if it is already in sys.modules)
            importlib.import_module('.' + name, 'labscript_devices')
        except ImportError:
            msg = """No %s registered for a device named %s. Ensure that there is a file
                'register_classes.py' with a call to
                labscript_devices.register_classes() for this device, with the device
                name passed to register_classes() matching the name of the device class.
                Fallback method of looking for and importing a module in
                labscript_devices with the same name as the device also failed. If using
                this method, check that the module exists, has the same name as the
                device class, and can be imported with no errors. Import error
                was:\n\n"""
            msg = dedent(msg) % (self.instancename, name) + traceback.format_exc()
            raise ImportError(msg)
        # Class definitions in that module have executed now, check to see if class is in our register:
        try:
            return self.registered_classes[name]
        except KeyError:
            # No? No such class is defined then, or maybe the user forgot to decorate it.
            raise ValueError(f'No class decorated as a {self.instancename} found in module labscript_devices.{name}, '
                             f'Did you forget to decorate the class definition with @{self.instancename}?')


# Decorating labscript device classes and BLACS worker classes was never used for
# anything and has been deprecated. These decorators can be removed with no ill
# effects. Do nothing, and emit a warning telling the user this.
def deprecated_decorator(name):
    def null_decorator(cls):
        msg = f'@{name} decorator is unnecessary and can be removed'
        warnings.warn(msg, stacklevel=2)
        return cls

    return null_decorator


labscript_device = deprecated_decorator('labscript_device')
BLACS_worker = deprecated_decorator('BLACS_worker')


# Registers for the decorator mechanism, which get_BLACS_tab() and
# get_runviewer_parser() fall back on when register_classes() has no entry.
BLACS_tab = ClassRegister('BLACS_tab')
runviewer_parser = ClassRegister('runviewer_parser')


def import_class_by_fullname(fullname):
    """Import and return a class from its fully qualified name.

    The name is the absolute import path, such as ``"module.submodule.ClassName"``.
    """
    split = fullname.split('.')
    module_name = '.'.join(split[:-1])
    class_name = split[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def deprecated_import_alias(fullname):
    """Allow a class to be imported from an old location.

    Returns a callable that calls the class with the arguments it is given. The
    class is not imported until the callable is first called, and a warning then
    points to the new import location. Use it in the module where the class used
    to be::

        ClassName = deprecated_import_alias("new.path.to.ClassName")
    """
    calling_module_name = inspect.getmodule(inspect.stack()[1][0]).__name__
    cls = []
    def wrapper(*args, **kwargs):
        if not cls:
            cls.append(import_class_by_fullname(fullname))
            shortname = fullname.split('.')[-1]
            newmodule = '.'.join(fullname.split('.')[:-1])
            msg = """Importing %s from %s is deprecated, please instead import it from
               %s. Importing anyway for backward compatibility, but this may cause some
               unexpected behaviour."""
            msg = dedent(msg) % (shortname, calling_module_name, newmodule)
            warnings.warn(msg, stacklevel=2)
        return cls[0](*args, **kwargs)
    return wrapper


# Dictionaries containing the import paths to BLACS tab and runviewer parser classes,
# not the classes themselves. These will be populated by calls to register_classes from
# code within register_classes.py files within subfolders of labscript_devices.
BLACS_tab_registry = {}
runviewer_parser_registry = {}
# The script files that registered each device, for use in error messages:
_register_classes_script_files = {}

def get_BLACS_tab(name):
    """Return the BLACS tab class of a labscript device.

    The class is the one named in a `register_classes` call for the device, or
    else the one decorated with `BLACS_tab` in labscript_devices/<name>.py.

    Raises
    ------
    ImportError, ValueError
        If neither method finds the class, as for indexing a `ClassRegister`.
    """
    if not BLACS_tab_registry:
        populate_registry()
    if name in BLACS_tab_registry:
        return import_class_by_fullname(BLACS_tab_registry[name])
    # Fall back on file naming convention + decorator method:
    return BLACS_tab[name]


def get_runviewer_parser(name):
    """Return the runviewer parser class of a labscript device.

    The class is the one named in a `register_classes` call for the device, or
    else the one decorated with `runviewer_parser` in labscript_devices/<name>.py.

    Raises
    ------
    ImportError, ValueError
        If neither method finds the class, as for indexing a `ClassRegister`.
    """
    if not runviewer_parser_registry:
        populate_registry()
    if name in runviewer_parser_registry:
        return import_class_by_fullname(runviewer_parser_registry[name])
    # Fall back on file naming convention + decorator method:
    return runviewer_parser[name]


def register_classes(labscript_device_name, BLACS_tab=None, runviewer_parser=None):
    """Register the BLACS tab and runviewer parser classes of a labscript device.

    Call this from a file called ``register_classes.py`` in a subfolder of
    labscript_devices. `get_BLACS_tab` and `get_runviewer_parser` find and run
    all such files through `populate_registry` before looking up a class.

    Parameters
    ----------
    BLACS_tab, runviewer_parser : str, optional
        The fully qualified import paths of the BLACS tab and runviewer parser
        classes, such as ``"labscript_devices.DeviceName.DeviceTab"``. They
        need not be in the same module as the device class, but should be
        within labscript_devices.

    Raises
    ------
    ValueError
        If a device of this name has already been registered.
    """
    if labscript_device_name in _register_classes_script_files:
        other_script =_register_classes_script_files[labscript_device_name]
        msg = """A device named %s has already been registered by the script %s.
            Labscript devices must have unique names."""
        raise ValueError(dedent(msg) % (labscript_device_name, other_script))
    BLACS_tab_registry[labscript_device_name] = BLACS_tab
    runviewer_parser_registry[labscript_device_name] = runviewer_parser
    script_filename = os.path.abspath(inspect.stack()[1][0].f_code.co_filename)
    _register_classes_script_files[labscript_device_name] = script_filename


def populate_registry():
    """Run every ``register_classes.py`` in the device folders.

    The folders are those in `LABSCRIPT_DEVICES_DIRS`, searched recursively.
    """
    for devices_dir in LABSCRIPT_DEVICES_DIRS:
        for folder, _, filenames in os.walk(devices_dir):
            if 'register_classes.py' in filenames:
                # Run the file without importing it: importing would need a unique name
                # for each in sys.modules, and we only need the calls it makes.
                spec = importlib.machinery.PathFinder.find_spec('register_classes', [folder])
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
