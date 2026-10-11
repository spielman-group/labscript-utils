#####################################################################
#                                                                   #
# __init__.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import os
import importlib
from .UnitConversionBase import UnitConversion


class _All:
    """Lazy ``__all__`` for ``from labscript_utils.unitconversions import *``.

    Importing every conversion module is slow, so it waits until a star import first
    asks for the names. This keeps old importers able to find all unit conversion
    classes in this namespace.
    """

    __all__ = None

    def __getitem__(self, ix):
        if self.__all__ is None:
            self._import_all()
        return self.__all__[ix]

    def _import_all(self):
        """Import every conversion module of this package into this module's globals."""
        if self.__all__ is None:
            self.__all__ = []
        for filename in os.listdir(os.path.split(__file__)[0]):
            if filename.endswith('.py') and filename != '__init__.py':
                module = filename[:-3]
                result = {}
                exec(f'from labscript_utils.unitconversions.{module} import *', result, result)
                for name, value in result.items():
                    globals()[name] = value
                    if isinstance(value, type) and issubclass(value, UnitConversion):
                        self.__all__.append(name)
                        # Full names for an older BLACS; due for removal in future.
                        fullname = f'labscript_utils.unitconversions.{module}.{name}'
                        globals()[fullname] = value


__all__ = _All()


def get_unit_conversion_class(fullname):
    """Import and return the unit conversion class with the given name.

    Parameters
    ----------
    fullname : str
        Fully qualified class name with an absolute import path, such as
        ``path.to.some.module.ClassName``. A bare class name is also accepted, for old
        shot files that do not save the full name; it is looked up among the names of
        every module in this package.

    Returns
    -------
    type
        The unit conversion class.

    Raises
    ------
    KeyError
        If a bare class name is not defined in this package.
    ImportError
        If the module of a fully qualified name cannot be imported.
    AttributeError
        If the module of a fully qualified name does not define the class.
    """
    if '.' not in fullname:
        if __all__.__all__ is None:
            __all__._import_all()
        return globals()[fullname]
    split = fullname.split('.')
    module_name = '.'.join(split[:-1])
    class_name = split[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
