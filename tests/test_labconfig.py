#####################################################################
#                                                                   #
# /tests/test_labconfig.py                                          #
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
"""App configs: the name of the file save_appconfig writes, for every name it can
be given, a save cut short, and a legacy INI config read through load_appconfig.
Labconfigs: a legacy experiment_name.

A save panel can hand back a name without the extension it was offered, or with
one the host chose, so the name save_appconfig receives is not always the name
asked for.
"""
import os
import warnings

import pytest

from labscript_utils.labconfig import LabConfig, load_appconfig, save_appconfig


@pytest.mark.parametrize(
    'given, written',
    [
        ('test', 'test.toml'),
        ('test.toml', 'test.toml'),
        # An extension that is not an app config's is part of the name:
        ('test.cfg', 'test.cfg.toml'),
        # A legacy INI name is the same configuration, so TOML replaces it:
        ('test.ini', 'test.toml'),
        ('rb.87.imaging', 'rb.87.imaging.toml'),
    ],
)
def test_save_appconfig_names_the_file_it_writes(tmp_path, given, written):
    save_appconfig(tmp_path / given, {'state': {'value': 1}})
    assert os.listdir(tmp_path) == [written]


def test_a_save_cut_short_leaves_the_old_config(tmp_path, monkeypatch):
    path = save_appconfig(tmp_path / 'app', {'state': {'value': 1}})

    def interrupt(*args):
        raise KeyboardInterrupt

    # The last step of a save, by which point a write in place has truncated it:
    monkeypatch.setattr(os, 'replace', interrupt)
    with pytest.raises(KeyboardInterrupt):
        save_appconfig(path, {'state': {'value': 2}})

    assert load_appconfig(path) == {'state': {'value': 1}}
    assert os.listdir(tmp_path) == ['app.toml']


def test_a_legacy_ini_config_is_read_converted_and_warned_of(tmp_path):
    ini = tmp_path / 'app.ini'
    ini.write_text('[state]\nvalue = 1\n')

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        data = load_appconfig(tmp_path / 'app.toml')

    assert data == {'state': {'value': 1}}
    assert (tmp_path / 'app.toml').exists()
    assert [warning.category for warning in caught] == [FutureWarning]
    assert str(ini) in str(caught[0].message)


def test_a_legacy_experiment_name_warns_once_naming_its_file(tmp_path):
    first, second = tmp_path / 'first.toml', tmp_path / 'second.toml'
    first.write_text("[default]\nuser = 'test'\n")
    second.write_text("[default]\nexperiment_name = 'old'\n")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for _ in range(2):
            config = LabConfig([str(first), str(second)])

    assert config.get('default', 'apparatus_name') == 'old'
    assert [warning.category for warning in caught] == [FutureWarning]
    assert str(second) in str(caught[0].message)
