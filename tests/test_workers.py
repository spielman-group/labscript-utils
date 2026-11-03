#####################################################################
#                                                                   #
# /tests/test_workers.py                                            #
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
"""Generator states run real worker jobs and release their resources on close."""
import os
from pathlib import Path
import threading
import time

import pytest
import zmq
from qtutils.qt.QtWidgets import QApplication
from zprocess.remote.server import RemoteProcessServer

from labscript_utils import workers
from labscript_utils.ls_zprocess import ProcessTree, get_config
from labscript_utils.workers import Worker, WorkersMixin, define_state


class EchoWorker(Worker):
    fail_init = False
    shutdown_delay = 0

    def init(self):
        if self.fail_init:
            raise RuntimeError('init failed')
        self.initialised = True

    def echo(self, value):
        assert self.initialised
        return value

    def fail(self):
        raise RuntimeError('job failed')

    def exit(self):
        raise SystemExit(7)

    def die(self):
        os._exit(1)

    @property
    def die_before_start(self):
        os._exit(1)

    def sleep(self, seconds):
        Path(self.directory, 'started').touch()
        time.sleep(seconds)
        return seconds

    def shutdown(self):
        time.sleep(self.shutdown_delay)
        with open(Path(self.directory, 'shutdown'), 'a') as log:
            log.write('s')


class Host(WorkersMixin):
    def __init__(self, remote_process_client=None):
        self.results = []
        self.errors = []
        self._init_workers(
            'workers_test', 'host', remote_process_client=remote_process_client
        )

    def _worker_job_finished(self, success, message):
        if not success:
            self.errors.append(message)

    def _worker_fatal_error(self, message):
        self.errors.append(message)

    @define_state(1, True)
    def call(self, method, *args):
        result = yield self.queue_work('w', method, *args)
        assert threading.current_thread() is threading.main_thread()
        self.results.append(result)


def wait_until(condition, timeout=10):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, 'Timed out'
        QApplication.processEvents()
        time.sleep(0.01)


@pytest.fixture(scope="module")
def qapplication():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def host(qapplication):
    host = Host()
    yield host
    host.close_workers()
    host.finalise_workers()


@pytest.fixture
def remote_host(qapplication, monkeypatch):
    config = get_config()
    server = RemoteProcessServer(
        bind_address='tcp://127.0.0.1', silent=True,
        shared_secret=config['shared_secret'], allow_insecure=config['allow_insecure'],
    )
    monkeypatch.setenv(
        'PYTHONPATH', str(Path(__file__).parent) + os.pathsep + os.environ.get('PYTHONPATH', '')
    )
    host = Host(ProcessTree.instance().remote_process_client('localhost', server.port))
    try:
        yield host, server
    finally:
        host.close_workers()
        host.finalise_workers()
        server.shutdown()


@pytest.mark.parametrize('method, error', [('fail', 'job failed'), ('exit', 'SystemExit: 7')])
def test_jobs_run_after_init_in_order_and_resume_after_a_job_error(
    host, tmp_path, method, error
):
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path)})
    host.call('sleep', 1.2)
    host.call('echo', 7)
    host.call(method)
    host.call('echo', 8)
    wait_until(lambda: len(host.results) == 4)
    assert host.results == [1.2, 7, None, 8]
    assert error in host.errors[0]
    host.close_workers()
    host.finalise_workers()
    assert (tmp_path / 'shutdown').read_text() == 's'


@pytest.mark.parametrize('fail_init, method, error', [
    (True, 'echo', 'init failed'),
    (False, 'missing', 'AttributeError'),
])
def test_init_or_lookup_failure_stops_queued_states(host, tmp_path, fail_init, method, error):
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path), 'fail_init': fail_init})
    host.call(method, 1)
    host.call('echo', 2)
    wait_until(lambda: host.state == 'fatal error')
    assert error in '\n'.join(host.errors)
    assert host.results == []


def test_closing_a_busy_worker_interrupts_it_and_shuts_down_once(host, tmp_path):
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path)})
    host.call('sleep', 60)
    wait_until(lambda: (tmp_path / 'started').exists())
    host.close_workers()
    host.finalise_workers()
    assert (tmp_path / 'shutdown').read_text() == 's'
    assert host.results == []


@pytest.mark.parametrize('method', ['die_before_start', 'die'])
def test_a_worker_exit_ends_the_wait_for_either_reply(host, tmp_path, method):
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path)})
    host.call('echo', 'ready')
    wait_until(lambda: host.results == ['ready'], timeout=30)
    host.results.clear()
    host.call(method)
    wait_until(lambda: host.state == 'fatal error', timeout=4)
    assert 'exited' in '\n'.join(host.errors)
    assert host.results == []


@pytest.mark.parametrize('phase', ['startup', 'shutdown'])
def test_forced_termination_confirms_exit(host, tmp_path, monkeypatch, phase):
    if phase == 'startup':
        marker = tmp_path / 'importing'
        (tmp_path / 'slow_worker.py').write_text(
            f'from pathlib import Path\nimport time\nPath({str(marker)!r}).touch()\n'
            'time.sleep(60)\nfrom labscript_utils.workers import Worker\n'
        )
        monkeypatch.setenv(
            'PYTHONPATH', str(tmp_path) + os.pathsep + os.environ.get('PYTHONPATH', '')
        )
        host.create_worker('w', 'slow_worker.Worker')
        wait_until(marker.exists, timeout=30)
    else:
        monkeypatch.setattr(workers, 'WORKER_QUIT_TIMEOUT', 0.1)
        host.create_worker('w', EchoWorker, {'directory': str(tmp_path), 'shutdown_delay': 60})
        host.call('echo', 'ready')
        wait_until(lambda: host.results == ['ready'], timeout=30)
    process = host.workers['w'][0]
    host.close_workers()
    assert host.finalise_workers() is True
    assert process.child.poll() is not None
    assert not host.workers


def test_unconfirmed_remote_exit_is_retained_until_a_later_attempt(
    remote_host, tmp_path, monkeypatch, caplog
):
    host, server = remote_host
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path)})
    host.call('echo', 'ready')
    wait_until(lambda: host.results == ['ready'], timeout=30)
    release = threading.Event()
    poll = server.proxy_poll

    def delayed_poll(pid):
        assert release.wait(15)
        return poll(pid)

    monkeypatch.setattr(server, 'proxy_poll', delayed_poll)
    try:
        host.close_workers()
        assert host.finalise_workers() is False
        assert 'w' in host.workers
        assert 'worker w on host localhost' in caplog.text
    finally:
        release.set()
    assert host.finalise_workers() is True
    assert not host.workers


def test_delivery_to_a_disconnected_remote_worker_fails_without_replay(remote_host, tmp_path):
    host, server = remote_host
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path)})
    host.call('echo', 'ready')
    wait_until(lambda: host.results == ['ready'], timeout=30)
    process, sending, _ = host.workers['w']
    monitor = sending.sock.get_monitor_socket(events=zmq.EVENT_DISCONNECTED)
    try:
        child = server.children[process.child.pid]
        child.kill()
        child.wait(timeout=5)
        assert monitor.poll(5000), 'The worker connection did not close'
        monitor.recv_multipart()
        host.call('echo', 'must not run')
        wait_until(lambda: host.state == 'fatal error', timeout=7)
        assert 'put() timed out' in '\n'.join(host.errors)
        assert host.results == ['ready']
    finally:
        sending.sock.disable_monitor()
        monitor.close()


def test_killed_remote_workers_share_one_confirmation_period(remote_host, tmp_path, monkeypatch):
    host, server = remote_host
    monkeypatch.setattr(workers, 'WORKER_QUIT_TIMEOUT', 0.1)
    for name in ('w', 'other'):
        host.create_worker(name, EchoWorker, {'directory': str(tmp_path), 'shutdown_delay': 60})
    host.call('echo', 'ready')
    wait_until(lambda: host.results == ['ready'], timeout=30)
    release = threading.Event()
    poll = server.proxy_poll

    def delayed_after_exit(pid):
        if server.children[pid].poll() is not None:
            assert release.wait(15)
        return poll(pid)

    monkeypatch.setattr(server, 'proxy_poll', delayed_after_exit)
    try:
        host.close_workers()
        began = time.monotonic()
        assert host.finalise_workers() is False
        assert time.monotonic() - began < 8
        assert set(host.workers) == {'w', 'other'}
    finally:
        release.set()
    assert host.finalise_workers() is True


def test_a_remote_server_that_lost_the_pid_does_not_confirm_exit(remote_host, tmp_path):
    host, server = remote_host
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path), 'shutdown_delay': 60})
    host.call('echo', 'ready')
    wait_until(lambda: host.results == ['ready'], timeout=30)
    pid = host.workers['w'][0].child.pid
    child = server.children.pop(pid)
    try:
        host.close_workers()
        assert host.finalise_workers() is False
        assert 'w' in host.workers
        assert child.poll() is None
    finally:
        server.children[pid] = child
        child.kill()
        child.wait(timeout=5)
    assert host.finalise_workers() is True
