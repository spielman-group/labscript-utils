# -*- coding: UTF-8 -*-
#####################################################################
#                                                                   #
# UnitConversionBase.py                                             #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
# copy, math and MethodType are unused here, but they reach every conversion module
# through its `from .UnitConversionBase import *`.
import copy
from types import MethodType
import math
from numpy import iterable, array


class _MultiplicativeConversion:
    """Scales another conversion by a constant factor."""

    def __init__(self, name, unprefixed_method, factor, to_base):
        self.unprefixed_method = unprefixed_method
        self.factor = float(factor)
        self.to_base = bool(to_base)
        self.__name__ = name

    def __call__(self, value):
        if self.to_base:
            return self.unprefixed_method(value * self.factor)
        else:
            return self.unprefixed_method(value) / self.factor


def vectorise(method):
    """Make a conversion method accept an iterable as well as a scalar.

    An iterable argument gives a numpy array with the method applied to each element.
    """
    def f(instance, arg):
        if iterable(arg):
            return array([method(instance, el) for el in arg])
        else:
            return method(instance, arg)
    return f


class UnitConversion:
    """Base class of the unit conversions of an output channel.

    A subclass sets the class attribute ``base_unit``, which must match the default
    hardware unit of the channel in its BLACS tab, and lists the units it converts to
    and from in ``derived_units``, either as a class attribute or on the instance
    before calling this constructor. For each derived unit ``<unit>`` it defines
    ``<unit>_to_base(self, value)`` and ``<unit>_from_base(self, value)``.

    Parameters
    ----------
    params : dict
        Calibration parameters. Its optional ``'magnitudes'`` entry lists the prefixes
        (``'p'``, ``'n'``, ``'u'``, ``'m'``, ``'k'``, ``'M'``, ``'G'``, ``'T'``) for which
        a prefixed copy of each derived unit is generated, such as ``'mA'`` for
        ``'A'``. The unicode micro sign is accepted for ``'u'``.

    Attributes
    ----------
    derived_units : list of str
        After construction, includes the prefixed units, ordered by the position of the
        unprefixed unit in the original list and then by magnitude.

    Raises
    ------
    AttributeError
        If a derived unit lacks its ``_to_base`` or ``_from_base`` method.
    KeyError
        If ``params['magnitudes']`` contains an unsupported prefix.
    """

    _magnitude_list = {'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'm': 1e-3,
                       'k': 1e3, 'M': 1e6, 'G': 1e9, 'T': 1e12}

    # Alias kept for backward compatibility.
    unit_list = _magnitude_list

    def __init__(self, params):
        magnitudes = params.get('magnitudes', [])

        # Accept the unicode micro sign for 'u'.
        magnitudes = [p if p != 'μ' else 'u' for p in magnitudes]
        self._magnitudes = {prefix: self._magnitude_list[prefix] for prefix in magnitudes}

        # (sort key, unit) pairs, sorted once the prefixed units have been added.
        derived_units_sortlist = []

        for i, derived_unit in enumerate(self.derived_units):
            sortinfo = (i, 1)
            derived_units_sortlist.append((sortinfo, derived_unit))

            # Create the methods of each prefixed unit from the unprefixed ones.
            unprefixed_to_base = getattr(self, derived_unit + "_to_base")
            unprefixed_from_base = getattr(self, derived_unit + "_from_base")
            for prefix, factor in self._magnitudes.items():
                unit = prefix + derived_unit
                to_base_name = unit + "_to_base"
                from_base_name = unit + "_from_base"
                self.__dict__[to_base_name] = _MultiplicativeConversion(
                    to_base_name, unprefixed_to_base, factor, to_base=True
                )
                self.__dict__[from_base_name] = _MultiplicativeConversion(
                    from_base_name, unprefixed_from_base, factor, to_base=False
                )

                sortinfo = (i, factor)
                derived_units_sortlist.append((sortinfo, unit))

        # Sort first by position of the unit in the original list of derived_units
        # without prefixes, then by magnitude.
        derived_units_sortlist.sort()
        self.derived_units = [unit for sortinfo, unit in derived_units_sortlist]

        # Alias kept for backward compatibility.
        self.units = self._magnitudes
