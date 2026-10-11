#####################################################################
#                                                                   #
# /labscript_profile/toml_config.py                                 #
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

import configparser
import tomllib

import tomli_w


def as_config_list(value):
    """Return a labconfig value as a list of stripped strings.

    Parameters
    ----------
    value : str, iterable or None
        A comma-separated string, a TOML array, or ``None``.

    Returns
    -------
    list of str
        The non-empty items, stripped; empty for ``None``.

    Raises
    ------
    TypeError
        If ``value`` is a single number or boolean.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(',') if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def load_toml_file(filename):
    """Return the contents of the TOML file ``filename`` as a dict."""
    with open(filename, 'rb') as f:
        return tomllib.load(f)


def dump_toml_file(filename, data):
    """Write the dict ``data`` to ``filename`` as TOML.

    The file is left intact if ``data`` cannot be serialised.
    """
    # Serialise before opening, so data TOML cannot hold leaves the file intact.
    text = tomli_w.dumps(data)
    with open(filename, 'wb') as f:
        f.write(text.encode('utf-8'))


class TomlBasicInterpolation(configparser.BasicInterpolation):
    """Basic interpolation that leaves non-string TOML values alone."""

    def before_get(self, parser, section, option, value, defaults):
        if not isinstance(value, str):
            return value
        return super().before_get(parser, section, option, value, defaults)


class TomlConfigParser(configparser.ConfigParser):
    """ConfigParser that keeps native TOML values and lowercases section names.

    The default section is ``default``. Values are stored as given, so a TOML
    array or number stays one, and ``getboolean`` accepts a real ``bool``.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_section', 'default')
        kwargs.setdefault('interpolation', TomlBasicInterpolation())
        super().__init__(*args, **kwargs)

    def _canonical_section_name(self, section):
        if section is None:
            return None
        return str(section).lower()

    def _normalize_loaded_sections(self):
        """Lowercase section names after a read, folding ``default`` into the defaults."""
        renamed_sections = {}
        migrated_defaults = {}
        for name, section_data in self._sections.items():
            canonical = self._canonical_section_name(name)
            if canonical == self.default_section:
                migrated_defaults.update(section_data)
                continue
            existing = renamed_sections.get(canonical)
            if existing is not None and existing is not section_data:
                raise configparser.DuplicateSectionError(canonical)
            renamed_sections[canonical] = section_data
        self._defaults.update(migrated_defaults)
        self._sections = renamed_sections
        self._proxies = {self.default_section: configparser.SectionProxy(self, self.default_section)}
        for canonical in renamed_sections:
            self._proxies[canonical] = configparser.SectionProxy(self, canonical)

    def add_section(self, section):
        return super().add_section(self._canonical_section_name(section))

    def has_section(self, section):
        return super().has_section(self._canonical_section_name(section))

    def options(self, section):
        return super().options(self._canonical_section_name(section))

    def has_option(self, section, option):
        return super().has_option(self._canonical_section_name(section), option)

    def remove_section(self, section):
        return super().remove_section(self._canonical_section_name(section))

    def remove_option(self, section, option):
        return super().remove_option(self._canonical_section_name(section), option)

    def __getitem__(self, key):
        return super().__getitem__(self._canonical_section_name(key))

    def set(self, section, option, value=None):
        section = self._canonical_section_name(section)
        if not section or section == self.default_section:
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise configparser.NoSectionError(section) from None
        sectdict[self.optionxform(option)] = value

    def getboolean(
        self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET
    ):
        value = self.get(section, option, raw=raw, vars=vars, fallback=fallback)
        if value is fallback:
            return value
        if isinstance(value, bool):
            return value
        if not isinstance(value, str):
            raise ValueError(f'Not a boolean: {value!r}')
        return self._convert_to_boolean(value)

    def get(self, section, option, *, raw=False, vars=None, fallback=configparser._UNSET):
        return super().get(
            self._canonical_section_name(section),
            option,
            raw=raw,
            vars=vars,
            fallback=fallback,
        )

    def items(self, section=configparser._UNSET, raw=False, vars=None):
        if section is configparser._UNSET:
            return super().items(section=section, raw=raw, vars=vars)
        return super().items(self._canonical_section_name(section), raw=raw, vars=vars)

    def read(self, filenames, encoding=None):
        read_ok = super().read(filenames, encoding=encoding)
        self._normalize_loaded_sections()
        return read_ok

    def read_toml(self, filename):
        """Read the TOML file ``filename`` into the parser, one section per table.

        Returns
        -------
        list of str
            ``[str(filename)]``, as ``read`` returns the files it read.

        Raises
        ------
        TypeError
            If a top-level entry of the file is not a table.
        """
        data = load_toml_file(filename)
        for section_name, section in data.items():
            if not isinstance(section, dict):
                raise TypeError(f"Section {section_name!r} must contain key/value pairs")
            section_name = self._canonical_section_name(section_name)
            if section_name != self.default_section and not self.has_section(section_name):
                self.add_section(section_name)
            for option, value in section.items():
                self.set(section_name, str(option), value)
        return [str(filename)]
