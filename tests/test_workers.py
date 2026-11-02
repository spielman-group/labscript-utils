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
from qtutils.qt.QtWidgets import QApplication

from labscript_utils.workers import Worker, WorkersMixin, define_state


class EchoWorker(Worker):
    fail_init = False

    def init(self):
        if self.fail_init:
            raise RuntimeError('init failed')
        self.initialised = True

    def echo(self, value):
        assert self.initialised
        return value

    def fail(self):
        raise RuntimeError('job failed')

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
        with open(Path(self.directory, 'shutdown'), 'a') as log:
            log.write('s')


class Host(WorkersMixin):
    def __init__(self):
        self.results = []
        self.errors = []
        self._init_workers('workers_test', 'host')

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


def test_jobs_run_after_init_in_order_and_resume_after_a_job_error(host, tmp_path):
    host.create_worker('w', EchoWorker, {'directory': str(tmp_path)})
    host.call('sleep', 1.2)
    host.call('echo', 7)
    host.call('fail')
    host.call('echo', 8)
    wait_until(lambda: len(host.results) == 4)
    assert host.results == [1.2, 7, None, 8]
    assert 'job failed' in host.errors[0]


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
