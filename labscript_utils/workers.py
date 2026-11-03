#####################################################################
#                                                                   #
# /labscript_utils/workers.py                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
"""Worker processes that run jobs for a parent, with BLACS's generator-based parent.

A :class:`Worker` runs in a process of its own and does the jobs its parent sends,
one at a time, in its main thread. A :class:`WorkersMixin` gives a class in the parent,
such as a lyse plugin, workers controlled by generator states in the GUI thread.
"""
from bisect import insort
import logging
import pickle
import queue
import signal
import sys
import threading
import time
import traceback
from types import GeneratorType
import warnings

from qtutils import inmain_decorator, inmain_later, inthread
from qtutils.qt.QtCore import QTimer
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


class Counter(object):
    """A class with a single method that
    returns a different integer each time it's called."""
    def __init__(self):
        self.i = 0
    def get(self):
        self.i += 1
        return self.i


get_unique_id = Counter().get


class StateQueue(object):
    """The queued states of a host, in order of priority and then of insertion. Only the
    main thread accesses the queue; put() called from another thread runs in the main
    thread."""

    def __init__(self, log_name, on_put):
        self.logger = logging.getLogger(log_name)
        self.logging_enabled = False
        if self.logging_enabled:
            self.logger.debug("started")

        self.list_of_states = []
        self._on_put = on_put

    def log_current_states(self):
        if self.logging_enabled:
            self.logger.debug('Current items in the state queue: %s', self.list_of_states)

    @inmain_decorator(True)
    def put(self, allowed_states, queue_state_indefinitely, delete_stale_states, data, priority=0):
        """Add a state to the queue. Lower number for priority indicates the state will
        be executed before any states with higher numbers for their priority"""
        # State data starts with priority, and then with a unique id that monotonically
        # increases. This way, sorting the queue will sort first by priority and then by
        # order added.
        state_data = [priority, get_unique_id(), allowed_states, queue_state_indefinitely, delete_stale_states,data]
        # Insert the task into the queue, retaining sort order first by priority and then by order added:
        insort(self.list_of_states, state_data)
        if self.logging_enabled:
            if not isinstance(data[0],str):
                self.logger.debug('New state queued up. Allowed modes: %d, queue state indefinitely: %s, delete stale states: %s, function: %s', allowed_states, queue_state_indefinitely, delete_stale_states, data[0].__name__)
        self.log_current_states()
        self._on_put()

    def get(self, state):
        """Remove and return the data of the first state that is allowed in the given
        mode, or None if there is none. States that are not queued indefinitely and come
        before it are removed."""
        # traverse the list
        delete_index_list = []
        success = False
        for i,item in enumerate(self.list_of_states):
            priority, unique_id, allowed_states, queue_state_indefinitely, delete_stale_states, data = item
            if self.logging_enabled:
                self.logger.debug('iterating over states in queue')
            if allowed_states&state:
                # We have found one! Remove it from the list
                delete_index_list.append(i)

                if self.logging_enabled:
                    self.logger.debug('requested state found in queue')

                # If we are to delete stale states, see if the next state is the same statefunction.
                # If it is, use that one, or whichever is the latest entry without encountering a different statefunction,
                # and delete the rest
                if delete_stale_states:
                    state_function = data[0]
                    i+=1
                    while i < len(self.list_of_states) and state_function == self.list_of_states[i][5][0]:
                        if self.logging_enabled:
                            self.logger.debug('requesting deletion of stale state')
                        priority, unique_id, allowed_states, queue_state_indefinitely, delete_stale_states, data = self.list_of_states[i]
                        delete_index_list.append(i)
                        i+=1

                success = True
                break
            elif not queue_state_indefinitely:
                if self.logging_enabled:
                    self.logger.debug('state should not be queued indefinitely')
                delete_index_list.append(i)

        # do this in reverse order so that the first delete operation doesn't mess up the indices of subsequent ones
        for index in reversed(sorted(delete_index_list)):
            if self.logging_enabled:
                self.logger.debug('deleting state')
            del self.list_of_states[index]

        if not success:
            data = None
        return data


class StateMachine(object):
    """Runs the queued states of a host in the main thread, one at a time. A state
    function that is a generator yields jobs for the workers. A job thread sends each
    job to its worker and waits for the result, and the result is sent into the
    generator in the main thread."""

    def __init__(self, host):
        self.host = host
        self.logger = logging.getLogger(f'{host._worker_log_name}.mainloop')
        self.event_queue = StateQueue(f'{host._worker_log_name}.state_queue', self.schedule)
        self.workers = host.workers
        self.closed = False
        self.failed = False
        self._scheduled = False
        self._state_name = None
        self._generator = None
        self._job = None
        self._job_success = True
        self._jobs = queue.Queue()
        self._thread = threading.Thread(target=self._job_loop, daemon=True)
        self._thread.start()
        self.logger.debug('Waiting for next event')

    def schedule(self):
        """Run the next state in a later iteration of the event loop. Called in the main
        thread."""
        if not self._scheduled:
            self._scheduled = True
            QTimer.singleShot(0, self._run_next_state)

    def _run_next_state(self):
        self._scheduled = False
        if self.closed or self.failed or self._state_name is not None:
            return
        data = self.event_queue.get(self.host.mode)
        if data is None:
            return
        func, (args, kwargs) = data
        self._state_name = func.__name__
        self._job = None
        self.logger.debug('Processing event %s', self._state_name)
        self.host.state = '%s (GUI)' % self._state_name
        try:
            generator = func(self.host, *args, **kwargs)
        except Exception:
            self._fatal_error(traceback.format_exc())
            return
        if isinstance(generator, GeneratorType):
            self._generator = generator
            self._advance(generator.__next__)
        else:
            self._state_finished()

    def _advance(self, step, *args):
        """Run the generator of the current state to its next yield, and pass the job
        that it yields to the job thread. A yield of None after the first yield repeats
        the previous job."""
        try:
            job = step(*args)
            if job or self._job is None:
                self._job = job
            worker_name, worker_function, _, _ = self._job
        except StopIteration:
            self.logger.debug('Finalising function')
            self._generator = None
            self._state_finished()
            return
        except Exception:
            self._fatal_error(traceback.format_exc())
            return
        self.logger.debug('Instructing worker %s to do job %s', worker_name, worker_function)
        if worker_function == 'init':
            self.host.state = 'Starting worker process (%s)' % worker_name
        else:
            self.host.state = '%s (%s)' % (worker_function, worker_name)
        self._jobs.put(self._job)

    def _state_finished(self):
        self._state_name = None
        if self.closed:
            return
        self.host.state = 'idle'
        self.logger.debug('Waiting for next event')
        self.schedule()

    def _job_loop(self):
        while True:
            job = self._jobs.get()
            if job is None:
                return
            try:
                result = self._do_job(*job)
            except Interrupted:
                self.logger.debug('Interrupted by host close, quitting job thread')
                return
            except Exception:
                inmain_later(self._fatal_error, traceback.format_exc())
                return
            inmain_later(self._job_done, *result)

    def _do_job(self, worker_name, worker_function, args, kwargs):
        """Send a job to a worker and return its success, error message and results.
        Runs in the job thread."""
        if worker_function == 'init':
            # Start the worker process before running its init() method:
            worker, _, _ = self.workers[worker_name]
            to_worker, from_worker = worker.start(*args)
            self.workers[worker_name] = (worker, to_worker, from_worker)
            args = ()
            del worker # Do not hold a reference indefinitely
            inmain_later(self._set_state, 'init (%s)' % worker_name)
        worker_arg_list = (worker_function, args, kwargs)
        try:
            pickle.dumps(worker_arg_list)
        except Exception as e:
            raise RuntimeError('Attempt to pass unserialisable object to child process') from e
        worker, to_worker, from_worker = self.workers[worker_name]
        to_worker.put(worker_arg_list, timeout=5)
        self.logger.debug('Waiting for worker to acknowledge job request')
        success, message, results = self._read_reply(worker, from_worker)
        if not success:
            self.logger.info('Worker reported failure to start job')
            raise RuntimeError(message)
        self.logger.debug('Worker reported job started, waiting for completion')
        success, message, results = self._read_reply(worker, from_worker)
        if success:
            self.logger.debug('Job completed')
        else:
            self.logger.info('Worker reported exception during job')
        return success, message, results

    def _read_reply(self, worker, from_worker):
        # ReadQueue does not see a dead peer. A read timeout checks liveness, not how
        # long a job may run; remote process requests retain BLACS's five-second bound.
        kwargs = {'get_timeout': 5} if worker.remote_process_client is not None else {}
        while True:
            try:
                return from_worker.get(timeout=_EXIT_CHECK_INTERVAL)
            except TimeoutError:
                if worker.child.poll(**kwargs) is not None:
                    # The reply may have arrived while the exit was being checked.
                    try:
                        return from_worker.get(timeout=0)
                    except TimeoutError:
                        raise ProcessExited('The worker exited during the job') from None

    def _set_state(self, state):
        if not self.closed:
            self.host.state = state

    def _job_done(self, success, message, results):
        if self.closed or self.failed:
            return
        self._job_success = success
        self.host._worker_job_finished(success, message)
        self.logger.debug('returning worker results to function %s', self._state_name)
        self.host.state = '%s (GUI)' % self._state_name
        self._advance(self._generator.send, results)

    def _fatal_error(self, message):
        """Stop running states and show the error. Called in the main thread."""
        if self.closed or self.failed:
            return
        self.failed = True
        self._generator = None
        self.logger.critical('A fatal exception happened:\n %s', message)
        self.host.state = 'fatal error'
        self.host._worker_fatal_error(message)
        self.logger.info('Exiting')
        inthread(self.host._end_workers)

    def close(self):
        """Stop running states, interrupt any communication with the workers, and stop
        the job thread. Called in the main thread."""
        if self.closed:
            return
        self.closed = True
        self._generator = None
        # A copy, as _end_workers pops the workers from another thread:
        for _, to_worker, from_worker in list(self.workers.values()):
            # Interrupt the read and write queues in case the job thread is blocking on
            # sending or receiving from them:
            if to_worker is not None:
                to_worker.interrupt()
                from_worker.interrupt()
        self._jobs.put(None)

    def join(self, timeout):
        self._thread.join(timeout)
        return not self._thread.is_alive()


def define_state(allowed_modes,queue_state_indefinitely,delete_stale_states=False):
    """Queue a decorated method as a GUI state, gated by the host's mode bitmask."""
    def wrap(function):
        unescaped_name = function.__name__
        escapedname = '_' + function.__name__
        def f(self,*args,**kwargs):
            function.__name__ = escapedname
            self.event_queue.put(allowed_modes,queue_state_indefinitely,delete_stale_states,[function,[args,kwargs]])
        f.__name__ = unescaped_name
        return f
    return wrap


class WorkersMixin:
    """BLACS's generator-based parent for local and remote workers.

    Call _init_workers in the GUI thread. States decorated with define_state yield
    queue_work requests and receive their results in that same thread. The host's
    mode gates states; state receives display text. Hosts override the concrete
    result/error methods below when they have their own UI.
    Normal delivery has a five-second queue timeout; execution duration is unlimited.
    The timeout does not preempt serialization or acquiring the queue mutex.

    Close the machine in the GUI thread, then finalise_workers from a thread that
    may block. A restart uses these same phases before rebuilding the host.
    """

    SHUTDOWN_TIMEOUT = 2
    mode = 1
    state = 'idle'

    def _init_workers(self, app_name, host_name, *, output_redirection_port=None,
                      remote_process_client=None, allowed_modes=1):
        """Set up one state machine, its job thread and its worker collection."""
        self._worker_app_name = app_name
        self._worker_host_name = host_name
        self._worker_log_name = f'{app_name}.{host_name}'
        self.logger = logging.getLogger(self._worker_log_name)
        self.output_redirection_port = output_redirection_port
        self.remote_process_client = remote_process_client
        self._worker_modes = allowed_modes
        self.workers = {}
        self._end_workers_lock = threading.Lock()
        self._statemachine = StateMachine(self)
        self.event_queue = self._statemachine.event_queue

    def _worker_run_args(self, worker_name, workerargs):
        return self._worker_app_name, worker_name, workerargs

    def _worker_job_finished(self, success, message):
        if not success:
            self.logger.error('Exception in worker:\n%s', message)

    def _worker_fatal_error(self, message):
        """The machine has stopped; a host may show the error in its UI."""

    def create_worker(self, name, WorkerClass, workerargs=None):
        """Create a local or remote worker and queue its init before ordinary states.

        WorkerClass is a Worker subclass or its import path, imported only in the
        child. The process starts when the queued initialisation state runs.
        """
        if workerargs is None:
            workerargs = {}
        if name in self.workers:
            raise Exception('There is already a worker process with name: %s' % name)
        if isinstance(WorkerClass, type):
            worker = WorkerClass(
                ProcessTree.instance(),
                output_redirection_port=self.output_redirection_port,
                remote_process_client=self.remote_process_client,
                startup_timeout=30
                )
        elif isinstance(WorkerClass, str):
            # If we were passed a string for the WorkerClass, it is an import path
            # for where the Worker class can be found. Pass it to zprocess.Process,
            # which will do the import in the subprocess only.
            worker = Process(
                ProcessTree.instance(),
                output_redirection_port=self.output_redirection_port,
                remote_process_client=self.remote_process_client,
                startup_timeout=30,
                subclass_fullname=WorkerClass
            )
        else:
            raise TypeError(WorkerClass)
        self.workers[name] = (worker, None, None)
        self.event_queue.put(
            self._worker_modes, True, False,
            [type(self)._initialise_worker, [(name, workerargs), {}]], priority=-1,
        )

    def _initialise_worker(self, worker_name, workerargs):
        yield self.queue_work(worker_name, 'init', *self._worker_run_args(worker_name, workerargs))
        if not self._statemachine._job_success:
            raise RuntimeError('Worker failed to initialise')

    def queue_work(self, worker_process, worker_function, *args, **kwargs):
        """Yield this request from a state to receive the worker method's result."""
        return worker_process, worker_function, args, kwargs

    def close_workers(self):
        """Stop states and interrupt worker communication, in the GUI thread."""
        self._statemachine.close()

    def finalise_workers(self):
        """Interrupt startup, join the job thread and end workers; may block.

        Return whether every worker's exit was confirmed; retain unconfirmed workers.
        Callers must not reinitialize or start replacements until this succeeds;
        retained records allow a later termination retry.
        """
        for worker, _, _ in list(self.workers.values()):
            worker.interrupt_startup()
        if not self._statemachine.join(2):
            self.logger.warning('job thread of %s did not stop', self._worker_host_name)
        return self._end_workers()

    def _end_workers(self):
        """Tell the workers to quit, and kill each one that has not exited after
        WORKER_QUIT_TIMEOUT seconds. A worker interrupts the job that it is running, and
        if the job has not stopped after WORKER_ABORT_TIMEOUT seconds, exits when it has
        no HDF5 file open for writing, or after WORKER_KILL_LOCK_TIMEOUT seconds. A
        worker that has not finished starting up is killed at once. A second call waits
        for the first to return. Killed workers share five seconds for exit confirmation.
        Return whether all exits were confirmed; retain unconfirmed workers."""
        with self._end_workers_lock:
            return self._end_workers_locked()

    def _end_workers_locked(self):
        if self.remote_process_client is not None:
            # Timeout for requests to the remote process server:
            kwargs = {'get_timeout': 5}
        else:
            kwargs = {}
        # Keep ownership until exit is confirmed, including when a remote server is lost.
        children = []
        killed = []
        for name, (worker, to_worker, _) in list(self.workers.items()):
            worker.interrupt_startup()
            if worker.child is None:
                del self.workers[name]
                continue
            if to_worker is not None:
                try:
                    # The queue's own interruptor is set when the state machine closes:
                    to_worker.put('quit', timeout=1, interruptor=Interruptor())
                except (TimeoutError, ProcessExited):
                    pass
                else:
                    children.append((name, worker.child))
                    continue
            try:
                worker.child.kill(**kwargs)
            except (OSError, TimeoutError):
                # The process has exited, or the remote process server is unreachable
                pass
            killed.append((name, worker.child))
        deadline = time.monotonic() + WORKER_QUIT_TIMEOUT
        for name, child in children:
            try:
                while True:
                    returncode = child.poll(**kwargs)
                    if returncode is not None:
                        # A restarted remote server can answer with an error string.
                        if isinstance(returncode, int):
                            del self.workers[name]
                        break
                    if time.monotonic() > deadline:
                        self.logger.warning(
                            "A worker of %s did not exit, killing it", self._worker_host_name
                        )
                        killed.append((name, child))
                        child.kill(**kwargs)
                        break
                    time.sleep(0.05)
            except (OSError, TimeoutError):
                pass
        deadline = time.monotonic() + 5
        for name, child in killed:
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    poll_kwargs = {'get_timeout': min(5, remaining)} if kwargs else {}
                    returncode = child.poll(**poll_kwargs)
                    if returncode is not None:
                        if isinstance(returncode, int):
                            del self.workers[name]
                        break
                    time.sleep(0.05)
            except (OSError, TimeoutError):
                pass
        for name, (worker, _, _) in self.workers.items():
            remote = worker.remote_process_client
            host = remote.host if remote is not None else 'localhost'
            self.logger.error('Could not confirm that worker %s on host %s stopped.',
                              name, host)
        return not self.workers

    def _shut_down_workers_then(self, callback):
        """Run the workers' shutdown() methods before any other state, and then close
        the state machine and call callback in the main thread, or call it after
        SHUTDOWN_TIMEOUT seconds if the shutdown() methods have not returned. If the
        state machine is not running, call callback at once. Called in the main
        thread."""
        if self._statemachine.closed or self._statemachine.failed:
            callback()
            return
        callbacks = [callback]

        def call_once():
            if callbacks:
                callbacks.pop()()

        self.event_queue.put(
            self._worker_modes,
            True,
            False,
            [WorkersMixin._shut_down_workers, [(call_once,), {}]],
            priority=-1,
        )
        QTimer.singleShot(int(self.SHUTDOWN_TIMEOUT * 1000), call_once)

    def _shut_down_workers(self, callback):
        for worker_name in self.workers:
            yield (self.queue_work(worker_name, 'shutdown'))
        # The workers are ended next, so no state may reopen the hardware:
        self._statemachine.close()
        callback()


class Worker(Process):
    """A process that runs the jobs its parent sends, one at a time, in its main thread.

    A subclass defines a method for each job, and may override :meth:`init`, its first
    job, and :meth:`shutdown`, which releases what the worker holds when it is told to
    quit or loses its parent. Each workerarg is an attribute of the worker before
    :meth:`init` runs.

    An Exception, KeyboardInterrupt or SystemExit raised by a job method is sent back
    as a failed job. Calling sys.exit() inside a method does not itself terminate
    the worker process: it remains available for subsequent jobs unless its parent
    ends it.
    """

    def init(self):
        """Prepare the worker. Its parent sends this as the worker's first job."""

    def shutdown(self):
        """Release what the worker holds, such as hardware, before the worker exits.

        It is called at most once, on a quit or a lost parent unless a ``shutdown`` job
        has started, and is never interrupted.
        """

    def run(self, app_name, worker_name, workerargs, *, log_name=None, protected_class=None):
        """Set up logging and the excepthook, set the workerargs and run the mainloop.

        Parameters
        ----------
        app_name : str
            The application's name, which ``setup_logging`` takes.
        worker_name : str
            The worker's name. The default logger and zlock identity is
            ``<app_name>.<worker_name>.worker``; log_name can supply a host's identity.
        workerargs : dict
            Each item becomes an attribute of the worker, overriding a class attribute
            of a subclass. A name that Worker or zprocess's Process uses is skipped with
            a warning.
        log_name : str, optional
            Logger and zlock identity; defaults to <app_name>.<worker_name>.worker.
        protected_class : type, optional
            The application's worker base, whose names workerargs cannot override.
        """
        self.worker_name = worker_name
        from labscript_utils.setup_logging import setup_logging
        setup_logging(app_name)
        if log_name is None:
            log_name = f'{app_name}.{worker_name}.worker'
        self.logger = logging.getLogger(log_name)
        self.logger.debug('Starting')
        import labscript_utils.excepthook
        labscript_utils.excepthook.install()
        labscript_utils.excepthook.set_logger(self.logger)
        import labscript_utils.h5_lock
        ProcessTree.instance().zlock_client.set_process_name(log_name)
        if protected_class is None:
            protected_class = Worker
        for name, value in workerargs.items():
            # Only the names that Worker and its bases use, on the class or the
            # instance, are protected: a subclass's class attribute is a default the
            # workerarg overrides.
            if hasattr(protected_class, name) or name in vars(self):
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
                except (Exception, KeyboardInterrupt, SystemExit):
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
