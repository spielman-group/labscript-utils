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
"""Worker processes run their parent's jobs, and fail them when they are gone."""
import os
from pathlib import Path
import time

import pytest

from labscript_utils.workers import Worker, WorkerError, WorkersMixin


class EchoWorker(Worker):
    fail_init = False

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
        with open(Path(self.directory, 'shutdown'), 'a') as f:
            f.write('s')


class Host(WorkersMixin):
    app_name = 'workers_test'


def start(tmp_path, **workerargs):
    host = Host()
    init = host.create_worker('w', EchoWorker, {'directory': str(tmp_path), **workerargs})
    return host, init


def test_a_job_returns_its_result_and_a_missing_method_fails(tmp_path):
    host, init = start(tmp_path)
    assert init.result(30) is None
    assert host.submit_job('w', 'echo', 7).result(30) == 7
    with pytest.raises(WorkerError, match='AttributeError'):
        host.submit_job('w', 'missing').result(30)
    assert host.submit_job('w', 'echo', 8).result(30) == 8
    host.end_workers()


def test_a_failed_init_fails_the_jobs_queued_behind_it(tmp_path):
    host, init = start(tmp_path, fail_init=True)
    queued = host.submit_job('w', 'echo', 1)
    with pytest.raises(WorkerError, match='init failed'):
        init.result(30)
    with pytest.raises(WorkerError, match='failed in init'):
        queued.result(30)
    host.end_workers()


def test_a_worker_that_dies_fails_its_jobs_and_restarts(tmp_path):
    host, init = start(tmp_path)
    init.result(30)
    jobs = [host.submit_job('w', 'die'), host.submit_job('w', 'echo', 1)]
    for job in jobs:
        with pytest.raises(WorkerError, match='exited'):
            job.result(30)
    host.restart_worker('w').result(30)
    assert host.submit_job('w', 'echo', 2).result(30) == 2
    host.end_workers()


def test_ending_a_busy_worker_interrupts_its_job_and_shuts_it_down_once(tmp_path):
    host, init = start(tmp_path)
    init.result(30)
    jobs = [host.submit_job('w', 'sleep'), host.submit_job('w', 'echo', 1)]
    while not (tmp_path / 'started').exists():
        time.sleep(0.01)
    host.end_workers()
    for job in jobs:
        with pytest.raises(WorkerError, match='was ended'):
            job.result(0)
    assert (tmp_path / 'shutdown').read_text() == 's'
