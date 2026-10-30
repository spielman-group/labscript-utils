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
"""Worker processes run their parent's jobs, fail them when they are gone, and release
what they hold once however they are ended."""
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from labscript_utils.workers import WORKER_QUIT_TIMEOUT, Worker, WorkerError, WorkersMixin


class EchoWorker(Worker):
    fail_init = False
    shutdown_delay = 0

    def init(self):
        if self.fail_init:
            raise RuntimeError('init failed')

    def echo(self, value):
        return value

    def die(self):
        os._exit(1)

    def sleep(self):
        Path(self.directory, 'started').touch()
        time.sleep(60)

    def shutdown(self):
        # Stands in for releasing hardware, such as NI-DAQmx tasks:
        Path(self.directory, 'shutting down').touch()
        time.sleep(self.shutdown_delay)
        with open(Path(self.directory, 'shutdown'), 'a') as f:
            f.write('s')


class Host(WorkersMixin):
    app_name = 'workers_test'


# Starts a worker, so that the test can kill its parent:
PARENT = '''
import sys, time
from test_workers import EchoWorker, Host
Host().create_worker('w', EchoWorker, {'directory': sys.argv[1]}).result(30)
print('ready', flush=True)
time.sleep(60)
'''


@pytest.fixture
def host():
    host = Host()
    yield host
    host.end_workers()


def start(host, tmp_path, **workerargs):
    return host.create_worker('w', EchoWorker, {'directory': str(tmp_path), **workerargs})


def wait_for(path, timeout=30):
    deadline = time.monotonic() + timeout
    while not path.exists():
        assert time.monotonic() < deadline, f'Timed out waiting for {path.name}'
        time.sleep(0.01)


def test_a_job_returns_its_result_and_a_missing_method_fails(host, tmp_path):
    assert start(host, tmp_path).result(30) is None
    assert host.submit_job('w', 'echo', 7).result(30) == 7
    with pytest.raises(WorkerError, match='AttributeError'):
        host.submit_job('w', 'missing').result(30)
    assert host.submit_job('w', 'echo', 8).result(30) == 8


def test_a_failed_init_fails_the_jobs_queued_behind_it(host, tmp_path):
    init = start(host, tmp_path, fail_init=True)
    queued = host.submit_job('w', 'echo', 1)
    with pytest.raises(WorkerError, match='init failed'):
        init.result(30)
    with pytest.raises(WorkerError, match='failed in init'):
        queued.result(30)


def test_a_worker_that_dies_fails_its_jobs_and_restarts(host, tmp_path):
    start(host, tmp_path).result(30)
    jobs = [host.submit_job('w', 'die'), host.submit_job('w', 'echo', 1)]
    for job in jobs:
        with pytest.raises(WorkerError, match='exited'):
            job.result(30)
    host.restart_worker('w').result(30)
    assert host.submit_job('w', 'echo', 2).result(30) == 2


def test_ending_a_busy_worker_interrupts_its_job_and_shuts_it_down_once(host, tmp_path):
    start(host, tmp_path).result(30)
    jobs = [host.submit_job('w', 'sleep'), host.submit_job('w', 'echo', 1)]
    wait_for(tmp_path / 'started')
    host.end_workers()
    for job in jobs:
        with pytest.raises(WorkerError, match='was ended'):
            job.result(0)
    assert (tmp_path / 'shutdown').read_text() == 's'


def test_a_shutdown_job_is_neither_interrupted_nor_repeated_by_the_quit(host, tmp_path):
    start(host, tmp_path, shutdown_delay=1).result(30)
    host.submit_job('w', 'shutdown')
    wait_for(tmp_path / 'shutting down')
    host.end_workers()
    assert (tmp_path / 'shutdown').read_text() == 's'


def test_a_hanging_shutdown_does_not_keep_the_worker_from_exiting(host, tmp_path):
    start(host, tmp_path, shutdown_delay=3600).result(30)
    began = time.monotonic()
    host.end_workers()
    assert (tmp_path / 'shutting down').exists()
    # Exited by itself, not killed when the parent's wait ran out:
    assert time.monotonic() - began < WORKER_QUIT_TIMEOUT


def test_a_worker_whose_parent_is_lost_shuts_down(tmp_path):
    parent = subprocess.Popen(
        [sys.executable, '-c', PARENT, str(tmp_path)],
        cwd=Path(__file__).parent, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert parent.stdout.readline() == 'ready\n'
    finally:
        parent.kill()
        parent.wait()
        parent.stdout.close()
    # Unanswered heartbeats take about 10 s to count as a lost parent:
    wait_for(tmp_path / 'shutdown', timeout=60)
