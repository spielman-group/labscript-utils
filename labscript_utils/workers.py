#####################################################################
#                                                                   #
# /labscript_utils/workers.py                                       #
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
"""Worker processes that run jobs for a parent, after BLACS's device tab workers.

A :class:`Worker` runs in a process of its own and does the jobs its parent sends,
one at a time, in its main thread. A :class:`WorkersMixin` gives a class in the parent,
such as a lyse plugin, workers that it starts, sends jobs, restarts and ends.
"""
from concurrent.futures import Future
import logging
import pickle
import queue
import signal
import sys
import threading
import time
import traceback
import warnings

from zprocess import Interrupted, Interruptor, Process, ProcessExited, interrupt_main_thread

from labscript_utils import dedent
from labscript_utils.ls_zprocess import ProcessTree

# Duration in seconds for which a worker that has been told to quit waits for its job,
# interrupted unless it is shutdown(), to stop:
WORKER_ABORT_TIMEOUT = 5
# Duration in seconds for which a worker that has been told to quit then waits for its
# shutdown() method to return:
WORKER_SHUTDOWN_TIMEOUT = 5
# Duration in seconds for which a worker with a job or shutdown() that did not finish
# waits for its HDF5 files to be closed before it exits:
WORKER_KILL_LOCK_TIMEOUT = 60
# Duration in seconds for which a parent waits for a worker to exit before killing it:
WORKER_QUIT_TIMEOUT = (
    WORKER_ABORT_TIMEOUT + WORKER_SHUTDOWN_TIMEOUT + WORKER_KILL_LOCK_TIMEOUT + 5
)
# Interval in seconds at which a parent waiting for a job's reply checks that the worker
# has not exited:
_EXIT_CHECK_INTERVAL = 1


class WorkerError(RuntimeError):
    """A job failed: it raised, its method is missing, or its worker is gone."""


class Worker(Process):
    """A process that runs the jobs its parent sends, one at a time, in its main thread.

    A subclass defines a method for each job, and may override :meth:`init`, its first
    job, and :meth:`shutdown`, which releases what the worker holds when it is told to
    quit or loses its parent. Each workerarg is an attribute of the worker before
    :meth:`init` runs.
    """

    def init(self):
        """Prepare the worker. Its parent sends this as the worker's first job."""

    def shutdown(self):
        """Release what the worker holds, such as hardware, before the worker exits.

        It is called at most once, on a quit or a lost parent unless a ``shutdown`` job
        has started, and is never interrupted.
        """

    def run(self, app_name, worker_name, workerargs):
        """Set up logging and the excepthook, set the workerargs and run the mainloop.

        Parameters
        ----------
        app_name : str
            The application's name, which ``setup_logging`` takes.
        worker_name : str
            The logger is ``<app_name>.<worker_name>.worker``, which is also the zlock
            process name. BLACS's names are ``<device>_<worker>``.
        workerargs : dict
            Each item becomes an attribute of the worker, overriding a class attribute
            of a subclass. A name that Worker or zprocess's Process uses is skipped with
            a warning.
        """
        self.worker_name = worker_name
        from labscript_utils.setup_logging import setup_logging
        setup_logging(app_name)
        log_name = f'{app_name}.{worker_name}.worker'
        self.logger = logging.getLogger(log_name)
        self.logger.debug('Starting')
        import labscript_utils.excepthook
        labscript_utils.excepthook.install()
        labscript_utils.excepthook.set_logger(self.logger)
        import labscript_utils.h5_lock
        ProcessTree.instance().zlock_client.set_process_name(log_name)
        for name, value in workerargs.items():
            # Only the names that Worker and its bases use, on the class or the
            # instance, are protected: a subclass's class attribute is a default the
            # workerarg overrides.
            if hasattr(Worker, name) or name in vars(self):
                msg = """attribute `{}` overwrites an attribute of the Worker base class
                    with the same name. This may cause unexpected behaviour. Consider
                    renaming it."""
                warnings.warn(dedent(msg).format(name), RuntimeWarning)
            else:
                setattr(self, name, value)
        self.mainloop()

    def mainloop(self):
        """Run jobs in the main thread. A thread receives the job requests from the
        parent, so that a request to quit is received while a job is running."""
        self._job_requests = queue.Queue()
        # Set while no job is running:
        self._idle = threading.Event()
        self._idle.set()
        # Set while the main thread is running a job other than shutdown(). _on_sigint()
        # raises KeyboardInterrupt only while this is set, so that the interrupt is
        # raised in the job and not in the code that runs after it:
        self._job_running = False
        # Held once the worker has started to quit:
        self._quitting = threading.Lock()
        # Whether shutdown() has been called, so that the quit does not call it again:
        self._shutdown_called = False
        signal.signal(signal.SIGINT, self._on_sigint)
        # Heartbeat failure quits as a quit message does, and ends the process
        # PARENT_DEATH_TIMEOUT seconds later, which leaves the quit its own deadlines:
        heartbeat_client = self.process_tree.heartbeat_client
        heartbeat_client.PARENT_DEATH_TIMEOUT = WORKER_ABORT_TIMEOUT + WORKER_SHUTDOWN_TIMEOUT + 5
        heartbeat_client.on_parent_death = self._on_parent_death
        threading.Thread(target=self._receive, daemon=True).start()
        while True:
            self.logger.debug('Waiting for next job request')
            request = self._job_requests.get()
            if self._quitting.locked():
                # Release the hardware, unless shutdown() has been called, and exit:
                if not self._shutdown_called:
                    try:
                        self.shutdown()
                    except Exception:
                        self.logger.exception('Exception in shutdown() on quit')
                sys.stdout.flush()
                sys.stderr.flush()
                self.kill_lock.exit_when_released(status=0, timeout=WORKER_KILL_LOCK_TIMEOUT)
            funcname, args, kwargs = request
            self._idle.clear()
            self.logger.debug('Got job request %s', funcname)
            try:
                func = getattr(self, funcname)
                success = True
                message = ''
            except AttributeError:
                success = False
                message = traceback.format_exc()
                self.logger.error("Couldn't start job:\n %s", message)
            # Report to the parent whether method lookup was successful or not:
            self._reply((success, message, None))
            if success:
                self.logger.debug('Starting job %s', funcname)
                try:
                    try:
                        # Set before the check, so that a quit after it interrupts any
                        # job but shutdown(), and one before it stops the job at once:
                        self._job_running = funcname != 'shutdown'
                        if self._quitting.locked():
                            raise KeyboardInterrupt
                        if funcname == 'shutdown':
                            self._shutdown_called = True
                        results = func(*args, **kwargs)
                    finally:
                        self._job_running = False
                    success = True
                    message = ''
                    self.logger.debug('Job complete')
                except (Exception, KeyboardInterrupt):
                    results = None
                    success = False
                    traceback_lines = traceback.format_exception(*sys.exc_info())
                    del traceback_lines[1]
                    message = ''.join(traceback_lines)
                    self.logger.error('Exception in job:\n%s', message)
                try:
                    pickle.dumps(results)
                except Exception:
                    message = traceback.format_exc()
                    self.logger.error('Job returned unserialisable datatypes, cannot pass them back to parent.\n%s', message)
                    message = 'Attempt to pass unserialisable object %s to parent process:\n' % str(results) + message
                    success = False
                    results = None
                # Report to the parent whether work was successful or not, and what the
                # results were:
                self._reply((success, message, results))
            self._idle.set()

    def _reply(self, reply):
        try:
            self.to_parent.put(reply)
        except Interrupted:
            # The parent is lost, and the worker is quitting.
            pass

    def _receive(self):
        while True:
            request = self.from_parent.get()
            if request == 'quit':
                self._quit()
            self._job_requests.put(request)

    def _quit(self):
        """Interrupt the job that is running, unless it is shutdown(), and have the main
        thread call shutdown(), unless it has been called, and exit. If the job has not
        stopped after WORKER_ABORT_TIMEOUT seconds, or the worker has not exited
        WORKER_SHUTDOWN_TIMEOUT seconds after it stopped, exit when no HDF5 file is open
        for writing, or after WORKER_KILL_LOCK_TIMEOUT seconds. Only the first call does
        anything."""
        if not self._quitting.acquire(blocking=False):
            return
        # Wake the main thread if it is waiting for a job request:
        self._job_requests.put('quit')
        if not self._idle.is_set():
            interrupt_main_thread()
        if self._idle.wait(WORKER_ABORT_TIMEOUT):
            time.sleep(WORKER_SHUTDOWN_TIMEOUT)
            reason = 'The worker did not exit %d seconds after its job stopped.' % (
                WORKER_SHUTDOWN_TIMEOUT
            )
        else:
            reason = 'The job did not stop after %d seconds.' % WORKER_ABORT_TIMEOUT
        print(
            reason + ' The worker will exit when it has no HDF5 file open for writing, '
            'or after %d seconds.' % WORKER_KILL_LOCK_TIMEOUT,
            file=sys.stderr,
        )
        sys.stdout.flush()
        sys.stderr.flush()
        self.kill_lock.exit_when_released(status=0, timeout=WORKER_KILL_LOCK_TIMEOUT)

    def _on_parent_death(self):
        # Without a shared secret, a send to a lost parent never returns, so interrupt
        # the main thread's:
        self.to_parent.interrupt()
        self._quit()

    def _on_sigint(self, signum, frame):
        if self._job_running:
            raise KeyboardInterrupt


class _WorkerRecord:
    """A worker's process, how to start it again, its queued jobs and its job thread."""

    def __init__(self, process, WorkerClass, workerargs):
        self.process = process
        self.WorkerClass = WorkerClass
        self.workerargs = workerargs
        # Items (future, method_name, args, kwargs), and None after the worker ends:
        self.jobs = queue.Queue()
        # Why the worker ended, or None while it runs:
        self.reason = None
        self.thread = None


# Guards every WorkersMixin's records, and their reasons and job queues:
_records_lock = threading.Lock()
# Set in the workers' job threads, where futures' callbacks run, so that ending a
# worker there, which waits for its job thread, is refused:
_job_thread = threading.local()


class WorkersMixin:
    """Worker processes for a class in the parent, such as a lyse plugin.

    The class sets ``app_name``, the name of the application, for the workers' logging,
    and may set ``output_redirection_port``, the port of an output box that shows the
    workers' output, which is otherwise printed. A worker runs its jobs in the order
    they are submitted, one at a time; one thread per worker sends them and completes
    their futures. When a worker exits, ends or restarts, its running and queued jobs
    fail. Keep the output box open until :meth:`end_workers` returns, so that it shows
    what the workers print as they quit. A future's callbacks run in its worker's job
    thread, so they must not call :meth:`restart_worker` or :meth:`end_workers`.
    """

    app_name = None
    output_redirection_port = None

    def _worker_records(self):
        # Created here, so that the class needs no __init__ of its own:
        return vars(self).setdefault('_workers', {})

    def _ending_lock(self):
        # Held while workers end, so that a second end or restart waits for the first:
        if getattr(_job_thread, 'active', False):
            raise RuntimeError(
                "Workers cannot be ended or restarted in a job thread, where futures' "
                "callbacks run"
            )
        return vars(self).setdefault('_workers_ending', threading.Lock())

    def create_worker(self, name, WorkerClass, workerargs=None):
        """Start a worker process, and queue its init() as its first job.

        The process is started at once, in the worker's job thread; BLACS's tabs start
        theirs at their first state instead.

        Parameters
        ----------
        name : str
            The worker's name among this object's workers, by which jobs are sent to it.
        WorkerClass : type or str
            A subclass of :class:`Worker`, or the import path of one, which is then
            imported in the worker process only.
        workerargs : dict, optional
            Attributes of the worker, as for :meth:`Worker.run`.

        Returns
        -------
        concurrent.futures.Future
            The future of init(). If the worker does not start or init() fails, it
            fails with :class:`WorkerError`, the worker is ended, and the jobs queued
            behind it fail.

        Raises
        ------
        ValueError
            If this object already has a worker called ``name``.
        """
        workerargs = dict(workerargs or {})
        kwargs = {
            'output_redirection_port': self.output_redirection_port,
            'startup_timeout': 30,
        }
        if isinstance(WorkerClass, str):
            process = Process(ProcessTree.instance(), subclass_fullname=WorkerClass, **kwargs)
        else:
            process = WorkerClass(ProcessTree.instance(), **kwargs)
        record = _WorkerRecord(process, WorkerClass, workerargs)
        future = Future()
        record.jobs.put((future, 'init', (), {}))
        record.thread = threading.Thread(
            target=self._run_jobs, args=(name, record), daemon=True
        )
        with _records_lock:
            records = self._worker_records()
            if name in records:
                raise ValueError(f'There is already a worker called {name}')
            record.thread.start()
            records[name] = record
        return future

    def submit_job(self, worker_name, method_name, *args, **kwargs):
        """Queue a job, a call of a method of a worker, and return its future.

        Parameters
        ----------
        worker_name : str
            The worker's name, as given to :meth:`create_worker`.
        method_name : str
            The name of the worker's method, which is called with ``args`` and
            ``kwargs``, which must be picklable, as must its result.

        Returns
        -------
        concurrent.futures.Future
            The future of the method's result. It fails with :class:`WorkerError` if
            the method raises or is missing, the arguments cannot be pickled, or the
            worker has exited, ends or restarts before the job is done.

        Raises
        ------
        ValueError
            If this object has no worker called ``worker_name``.
        """
        future = Future()
        with _records_lock:
            record = self._worker_records().get(worker_name)
            if record is None:
                raise ValueError(f'There is no worker called {worker_name}')
            if record.reason is not None:
                future.set_exception(WorkerError(f'The worker {worker_name} {record.reason}'))
            else:
                record.jobs.put((future, method_name, args, kwargs))
        return future

    def restart_worker(self, name):
        """End a worker as :meth:`end_workers` does, then create it again.

        It is created with the class and workerargs it was first created with.

        Returns
        -------
        concurrent.futures.Future
            The future of the new worker's init().

        Raises
        ------
        ValueError
            If this object has no worker called ``name``.
        RuntimeError
            If called in a job thread, as from a future's callback.
        """
        with self._ending_lock():
            with _records_lock:
                record = self._worker_records().pop(name, None)
            if record is None:
                raise ValueError(f'There is no worker called {name}')
            self._end([record], 'was restarted')
            return self.create_worker(name, record.WorkerClass, record.workerargs)

    def end_workers(self):
        """Tell the workers to quit, and kill each one that has not exited after
        WORKER_QUIT_TIMEOUT seconds.

        A worker interrupts the job that it is running, and if the job has not stopped
        after WORKER_ABORT_TIMEOUT seconds, exits when it has no HDF5 file open for
        writing, or after WORKER_KILL_LOCK_TIMEOUT seconds. A worker that has not
        finished starting up is killed at once. Their running and queued jobs fail.
        Returns once every worker has exited, so call it from a thread that may wait. A
        second call waits for the first. Raises RuntimeError if called in a job thread,
        as from a future's callback.
        """
        with self._ending_lock():
            with _records_lock:
                records = list(self._worker_records().values())
                self._worker_records().clear()
            self._end(records, 'was ended')

    def _end(self, records, reason):
        ending = [record for record in records if self._mark_ended(record, reason)]
        self._quit_processes(ending)
        for record in records:
            record.thread.join()

    def _mark_ended(self, record, reason):
        """Record why a worker ended and wake its job thread, which then fails its jobs.
        Return whether this call ended it."""
        with _records_lock:
            if record.reason is not None:
                return False
            record.reason = reason
            record.jobs.put(None)
            return True

    def _quit_processes(self, records):
        """Tell the workers' processes to quit, and kill each one that has not exited
        after WORKER_QUIT_TIMEOUT seconds, or at once if it has not started."""
        children = []
        for record in records:
            process = record.process
            process.interrupt_startup()
            if process.child is None:
                continue
            if process.to_child is not None:
                # Wakes the job thread if it is sending or waiting for a reply:
                process.to_child.interrupt()
                process.from_child.interrupt()
                try:
                    # A fresh interruptor, as the queue's own is set:
                    process.to_child.put('quit', timeout=1, interruptor=Interruptor())
                except (TimeoutError, ProcessExited):
                    pass
                else:
                    children.append(process.child)
                    continue
            try:
                process.child.kill()
            except OSError:
                pass
        deadline = time.monotonic() + WORKER_QUIT_TIMEOUT
        for child in children:
            while child.poll() is None:
                if time.monotonic() > deadline:
                    logging.getLogger(self.app_name).warning('A worker did not exit, killing it')
                    child.kill()
                    break
                time.sleep(0.05)

    def _run_jobs(self, name, record):
        """Start the worker, then send it its jobs in order and complete their futures,
        until it ends. Runs in the worker's job thread."""
        _job_thread.active = True
        process = record.process
        # Whether this thread ended the worker, and so must quit its process:
        must_quit = False
        try:
            process.start(self.app_name, name, record.workerargs)
        except Exception as e:
            must_quit = self._mark_ended(record, f'did not start: {e}')
        while True:
            job = record.jobs.get()
            if job is None:
                break
            future, method_name, args, kwargs = job
            if not future.set_running_or_notify_cancel():
                if method_name == 'init':
                    must_quit |= self._mark_ended(record, 'had its init() cancelled')
                continue
            if record.reason is not None:
                future.set_exception(WorkerError(f'The worker {name} {record.reason}'))
                continue
            try:
                future.set_result(self._do_job(process, method_name, args, kwargs))
            except WorkerError as e:
                future.set_exception(e)
                if method_name == 'init':
                    must_quit |= self._mark_ended(record, 'failed in init()')
            except (Interrupted, ProcessExited):
                self._mark_ended(record, 'exited')
                future.set_exception(WorkerError(f'The worker {name} {record.reason}'))
            except Exception as e:
                logging.getLogger(self.app_name).exception('Error in the job thread of %s', name)
                must_quit |= self._mark_ended(record, f'failed: {e!r}')
                future.set_exception(WorkerError(f'The worker {name} {record.reason}'))
        if must_quit:
            self._quit_processes([record])

    def _do_job(self, process, method_name, args, kwargs):
        """Send a job to the worker and return its result, read from its two replies, or
        one if its method is missing."""
        job = (method_name, args, kwargs)
        try:
            pickle.dumps(job)
        except Exception as e:
            raise WorkerError('Attempt to pass unserialisable object to child process') from e
        process.to_child.put(job)
        for _ in range(2):
            while True:
                # Once the worker has exited, a reply it sent first is still read:
                exited = process.child.poll() is not None
                try:
                    success, message, results = process.from_child.get(
                        timeout=0 if exited else _EXIT_CHECK_INTERVAL
                    )
                    break
                except TimeoutError:
                    if exited:
                        raise ProcessExited('The worker exited during the job') from None
            if not success:
                raise WorkerError(message)
        return results
