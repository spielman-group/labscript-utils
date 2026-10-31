#####################################################################
#                                                                   #
# /tests/test_ls_zprocess.py                                        #
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
"""A tool's client reaching its server through the shared request protocol."""
import socket
import sys
import threading

import pytest

import labscript_utils.ls_zprocess as ls_zprocess
from labscript_utils.labconfig import LabConfig
from labscript_utils.ls_zprocess import CommandHandler, ZMQClient, ZMQServer


class ShotServer(ZMQServer):
    server = 'shots'

    def handle_add(self, a, b=0):
        return a + b

    def handle_status(self, shot_id):
        return {'shot_42': 'done'}[shot_id]


class Optimizer(CommandHandler):
    def handle_start(self, runs):
        """Start an optimization of ``runs`` shots."""
        return f'started {runs}'


class History:
    def handle_clear(self):
        """Forget the past runs."""
        return 'cleared'


class ShotClient(ZMQClient):
    server = 'shots'
    # Nothing listens here, so a client that misread the labconfig times out.
    default_port = 1


@pytest.fixture
def server(monkeypatch, tmp_path):
    # The security settings still come from the machine's labconfig:
    ls_zprocess.get_config()
    with socket.socket() as free:
        free.bind(('localhost', 0))
        port = free.getsockname()[1]
    # A real labconfig, naming the test server, stands in for the machine's own.
    labconfig = tmp_path / 'labconfig.toml'
    labconfig.write_text(
        f"[servers]\nshots = 'localhost'\n\n[ports]\nshots = {port}\n\n"
        "[timeouts]\ncommunication_timeout = 5\n"
    )
    monkeypatch.setattr(
        ls_zprocess, 'LabConfig', lambda: LabConfig(config_path=labconfig)
    )
    server = ShotServer()
    try:
        yield server
    finally:
        server.shutdown()


@pytest.fixture
def client(server):
    return ShotClient()


def test_a_bound_client_reaches_its_bound_servers_handler(client):
    assert client.request('add', 2, b=3) == 5


def test_a_handler_exception_reaches_the_client_and_the_server_goes_on(
    client, monkeypatch
):
    hook_calls = []
    monkeypatch.setattr(sys, 'excepthook', lambda *args: hook_calls.append(args))
    monkeypatch.setattr(threading, 'excepthook', hook_calls.append)
    with pytest.raises(KeyError) as raised:
        client.request('status', 'shot_7')
    assert str(raised.value) == str(KeyError('shot_7'))
    assert 'handle_status' in raised.value.__notes__[-1]
    assert client.request('status', 'shot_42') == 'done'
    assert hook_calls == []


def test_a_second_server_on_a_port_in_use_names_it(client):
    with pytest.raises(OSError, match=r'shots cannot start because port \d+ is in use'):
        ShotServer()


def test_describe_gives_the_documented_commands_of_the_server_and_its_mounted_handlers(
    server, client
):
    optimizer = Optimizer()
    server.mount('optimizer', optimizer)
    optimizer.mount('history', History())
    assert client.request('optimizer.start', 3) == 'started 3'
    assert client.request('optimizer.history.clear') == 'cleared'
    with pytest.raises(ValueError, match='optimizer.stop'):
        client.request('optimizer.stop')
    tree = client.request('describe')
    # handle_add and handle_status have no docstrings:
    assert set(tree['commands']) == {'hello', 'describe'}
    assert tree['children'] == {'optimizer': {
        'commands': {'start': {
            'signature': '(runs)', 'description': 'Start an optimization of ``runs`` shots.'
        }},
        'children': {'history': {
            'commands': {'clear': {'signature': '()', 'description': 'Forget the past runs.'}},
            'children': {},
        }},
    }}
