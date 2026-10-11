#####################################################################
#                                                                   #
# ls_zprocess.py                                                    #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
"""Wrappers around zprocess objects, configured from the labconfig.

``ProcessTree``, ``ZMQServer``, ``ZMQClient`` and ``Context`` take their security
settings, and the zlock server's host and port, from LabConfig, so multiprocessing
done with them is configured by it. To configure such an object by hand,
instantiate the zprocess class directly. ``Lock``, ``Event``, ``Handler``,
``RemoteProcessClient`` and the ``zmq_get*`` and ``zmq_push*`` functions use the
shared ``ProcessTree`` and ``ZMQClient`` instances.
"""
import os
import pickle
import subprocess
import sys
import traceback
from socket import gethostbyname

import zmq
from packaging.version import Version

import zprocess
import zprocess.process_tree
import zprocess.remote
import zprocess.zlock
import zprocess.zlog
from zprocess import KillLock
from zprocess.security import SecureContext, SecureSocket

from labscript_utils import dedent
from labscript_utils.labconfig import LabConfig

kill_lock = KillLock()

_cached_config = None

_ERR_NO_SHARED_SECRET = """

--------

Security has not been configured. To create a new shared secret, run:

python -m zprocess.makesecret

move the resulting file somewhere (for example the labconfig directory)
and then add it to labconfig like:

[security]
shared_secret = %(labscript_suite)s/labconfig/zpsecret-09f6dfa0.key

You will need to copy the same shared secret to all computers running
the labscript suite that need to communicate with each other. Treat this
file like a password: it allows anyone on the same network acess to
labscript suite programs, most of of which are capable of remote code
execution. If you are on a trusted network and don't want to use encrypted
communication, you may instead set:

[security]
allow_insecure = True

in your configuration, but this is not advised."""


def get_config():
    """Return the zprocess settings from LabConfig, with defaults filled in.

    The result is cached, so LabConfig is read once per process.

    Returns
    -------
    dict
        The keys ``zlock_host``, ``zlock_port``, ``zlog_host``, ``zlog_port``,
        ``zprocess_remote_port``, ``shared_secret`` (the text of the file named by
        ``shared_secret_file``, or None), ``shared_secret_file``,
        ``allow_insecure``, ``logging_maxBytes`` and ``logging_backupCount``.

    Raises
    ------
    RuntimeError
        If the labconfig names no zlock server.
    ValueError
        If it configures neither a shared secret nor ``allow_insecure``.
    """
    global _cached_config
    # Cache the config so it is not loaded multiple times per process:
    if _cached_config is not None:
        return _cached_config

    labconfig = LabConfig()
    config = {}
    try:
        config['zlock_host'] = labconfig.get('servers', 'zlock')
    except (labconfig.NoOptionError, labconfig.NoSectionError):
        msg = "No zlock server specified in labconfig"
        raise RuntimeError(msg)
    config['zlock_port'] = labconfig.get(
        'ports', 'zlock', fallback=zprocess.zlock.DEFAULT_PORT
    )
    # We hard-code the zlog host and port, since zlog always runs on the computer with
    # the top-level process
    config['zlog_host'] = 'localhost'
    config['zlog_port'] = zprocess.zlog.DEFAULT_PORT
    config['zprocess_remote_port'] = labconfig.get(
        'ports', 'zprocess_remote', fallback=zprocess.remote.DEFAULT_PORT
    )
    shared_secret_file = labconfig.get('security', 'shared_secret', fallback=None)
    config['shared_secret'] = None
    if shared_secret_file is not None:
        with open(shared_secret_file) as f:
            config['shared_secret'] = f.read().strip()
    config['shared_secret_file'] = shared_secret_file
    config['allow_insecure'] = labconfig.getboolean(
        'security', 'allow_insecure', fallback=False
    )
    if config['shared_secret'] is None and not config['allow_insecure']:
        raise ValueError(_ERR_NO_SHARED_SECRET.replace('/', os.sep))
    config['logging_maxBytes'] = labconfig.getint(
        'logging', 'maxBytes', fallback=1024 * 1024 * 50
    )
    config['logging_backupCount'] = labconfig.getint(
        'logging', 'backupCount', fallback=1
    )
    _cached_config = config
    return config


class ProcessTree(zprocess.ProcessTree):
    """A ``zprocess.ProcessTree`` configured from LabConfig for security, zlock, zlog.

    Call ``instance()`` to get the singleton. The class can still be instantiated
    directly.
    """

    _instance = None

    @classmethod
    def instance(cls):
        """Return this process's ProcessTree, creating the singleton on first use."""
        # If we are already a child process, return the ProcessTree associated with the
        # connection to our parent. This may not even be an instance of this subclass,
        # but it will be if this subclass was used when calling connect_to_parent().
        instance = zprocess.ProcessTree.instance()
        if instance is not None:
            return instance
        # Otherwise, return previously initialised singleton for the top-level process:
        if cls._instance is not None:
            return cls._instance
        # Otherwise, create that singleton and return it:
        config = get_config()
        cls._instance = cls(
            shared_secret=config['shared_secret'],
            allow_insecure=config['allow_insecure'],
            zlock_host=config['zlock_host'],
            zlock_port=config['zlock_port'],
            zlog_host='localhost',
            zlog_port=config['zlog_port'],
        )
        # Assign this to the default zprocess ProcessTree so that code using deprecated
        # zprocess calls use this ProcessTree:
        zprocess.process_tree._default_process_tree = cls._instance
        # Assign the zlock client as the default zlock server so that code using
        # deprecated zlock calls can use it:
        zprocess.zlock._default_zlock_client = cls._instance.zlock_client

        return cls._instance


class ZMQServer(zprocess.ZMQServer):
    """A ``zprocess.ZMQServer`` configured with security settings from LabConfig.

    It takes the arguments of ``zprocess.ZMQServer`` except ``shared_secret`` and
    ``allow_insecure``, which come from LabConfig; passing either raises
    ``ValueError``.
    """

    def __init__(
        self,
        port=None,
        dtype='pyobj',
        pull_only=False,
        bind_address='tcp://*',
        timeout_interval=None,
        **kwargs
    ):
        for kwarg in ['shared_secret', 'allow_insecure']:
            if kwarg in kwargs:
                msg = f"""keyword argument {kwarg} not allowed - it will be set
                    according to LabConfig. To make a custom ZMQServer, use
                    zprocess.ZMQServer instead of
                    labscript_utils.ls_zprocess.ZMQServer"""
                raise ValueError(dedent(msg))

        config = get_config()
        shared_secret = config['shared_secret']
        allow_insecure = config['allow_insecure']

        super().__init__(
            port=port,
            dtype=dtype,
            pull_only=pull_only,
            bind_address=bind_address,
            shared_secret=shared_secret,
            allow_insecure=allow_insecure,
            timeout_interval=timeout_interval,
            **kwargs
        )

    def handler(self, request_data):
        """Answer ``[command, args, kwargs]`` by calling ``handle_<command>``.

        A subclass defines ``handle_`` methods rather than overriding this one.
        An exception is returned rather than raised, so the client raises it and
        this server opens no error dialog. It keeps its message, with the
        server's traceback attached as a note, and one the client could not
        unpickle or raise is sent as a ``RuntimeError`` instead.
        """
        try:
            command, args, kwargs = request_data
            return getattr(self, 'handle_' + command)(*args, **kwargs)
        except BaseException as e:
            note = f'{type(self).__name__} traceback:\n{traceback.format_exc()}'
            # zprocess's client raises only an Exception it can unpickle, and its
            # server meets an unpicklable reply with an error of its own. A class
            # from this process's __main__ pickles here but cannot unpickle there.
            try:
                pickle.loads(pickle.dumps(e, protocol=zprocess.PICKLE_PROTOCOL))
                sendable = isinstance(e, Exception) and type(e).__module__ != '__main__'
            except Exception:
                sendable = False
            if sendable:
                returned = e
            else:
                # The message names the class, since the class cannot go back. Line 0
                # is the exception itself; any notes it carries follow it, and already
                # travel in the traceback note.
                returned = RuntimeError(traceback.format_exception_only(e)[0].strip())
            returned.add_note(note)
            return returned

    def handle_hello(self):
        """Answer ``'hello'``, so a client can check that this server is up."""
        return 'hello'


class ZMQClient(zprocess.ZMQClient):
    """A ``zprocess.ZMQClient`` configured with security settings from LabConfig.

    Call ``instance()`` to get the singleton. The class can still be instantiated
    directly.

    A subclass binds to one server by setting ``server``, its name in the
    labconfig, and ``default_port``, and then sends it requests with
    :meth:`request`.
    """

    server = None
    default_port = None
    _instance = None

    def __init__(self, host=None, port=None, timeout=None):
        """Create a client, bound to ``server`` when the class names one.

        Parameters
        ----------
        host : str, optional
            For a bound client, defaults to the labconfig's ``servers/<server>``,
            else ``localhost``.
        port : int, optional
            For a bound client, defaults to the labconfig's ``ports/<server>``,
            else ``default_port``.
        timeout : float, optional
            For a bound client, defaults to the labconfig's
            ``timeouts/communication_timeout``, else 60 seconds.
        """
        config = get_config()
        super().__init__(
            shared_secret=config['shared_secret'],
            allow_insecure=config['allow_insecure'],
        )
        if self.server is not None and None in (host, port, timeout):
            labconfig = LabConfig()
            if host is None:
                host = labconfig.get('servers', self.server, fallback='localhost')
            if port is None:
                port = labconfig.getint(
                    'ports', self.server, fallback=self.default_port
                )
            if timeout is None:
                timeout = labconfig.getfloat(
                    'timeouts',
                    'communication_timeout',
                    fallback=60,
                )
        self.host = host
        self.port = port
        self.timeout = timeout

    @classmethod
    def instance(cls):
        """Return this class's singleton, creating it on first use."""
        # Only this class's own is looked at, so a subclass never returns its base
        # class's:
        if cls.__dict__.get('_instance') is None:
            cls._instance = cls()
        return cls._instance

    def request(self, command, *args, **kwargs):
        """Return the server's ``handle_<command>(*args, **kwargs)``.

        An exception it raises is raised here, with its own class and message.
        """
        return self.get(
            self.port, self.host, data=[command, args, kwargs], timeout=self.timeout
        )

    def say_hello(self, timeout=None):
        """Return the server's ``'hello'``, waiting ``timeout`` seconds if given."""
        if timeout is None:
            timeout = self.timeout
        return self.get(self.port, self.host, data=['hello', (), {}], timeout=timeout)


class Context(SecureContext):
    """A ``zprocess.security.SecureContext`` configured from LabConfig.

    It can replace a ``zmq.Context``. Instantiate it for a context of its own, or
    call ``instance()`` for a shared one, which only suits code that does not
    terminate its context.
    """

    def __init__(self, io_threads=1, shared_secret=None):
        config = get_config()
        # Allow shared_secret only if it matches what we expect. This is because
        # zprocess SecureContext.instance() will call our __init__ method with the
        # shared secret whether we like it or not, so let's cooperate with that.
        if shared_secret is not None and shared_secret != config['shared_secret']:
            msg = "shared_secret must be None or match labconfig"
            raise ValueError(msg)
        super().__init__(io_threads=io_threads, shared_secret=config['shared_secret'])

    @classmethod
    def instance(cls):
        """Return the shared context, creating it on first use."""
        config = get_config()
        return super().instance(shared_secret=config['shared_secret'])

    def socket(self, socket_type, socket_class=None, **kwargs):
        """Return a socket, secured by LabConfig's settings if it is a SecureSocket."""
        # socket_class kwarg introduced in pyzmq 25. Pass it through if it was given,
        # otherwise don't.
        if socket_class is not None:
            kwargs['socket_class'] = socket_class
        # Add the security argument only for a SecureSocket: a caller may ask for
        # another socket class, as ThreadAuthenticator does for its internal socket.
        if socket_class is None or issubclass(socket_class, SecureSocket):
            config = get_config()
            kwargs['allow_insecure'] = config['allow_insecure']
        return super().socket(socket_type=socket_type, **kwargs)


def Lock(*args, **kwargs):
    """Return a zlock lock; see ``zprocess.ProcessTree.lock``.

    A ``read_only`` argument is dropped unless ``connect_to_zlock_server`` has found
    that the zlock server supports read-write locks.
    """
    if 'read_only' in kwargs and not _zlock_server_supports_readwrite:
        del kwargs['read_only']
    return ProcessTree.instance().lock(*args, **kwargs)


def Event(*args, **kwargs):
    """Return an event on the shared ProcessTree; see ``zprocess.ProcessTree.event``."""
    return ProcessTree.instance().event(*args, **kwargs)


def Handler(*args, **kwargs):
    """Return a zlog logging handler; see ``zprocess.ProcessTree.logging_handler``."""
    return ProcessTree.instance().logging_handler(*args, **kwargs)


def zmq_get(*args, **kwargs):
    """Call ``get`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().get(*args, **kwargs)


def zmq_get_multipart(*args, **kwargs):
    """Call ``get_multipart`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().get_multipart(*args, **kwargs)


def zmq_get_string(*args, **kwargs):
    """Call ``get_string`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().get_string(*args, **kwargs)


def zmq_get_raw(*args, **kwargs):
    """Call ``get_raw`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().get_raw(*args, **kwargs)


def zmq_push(*args, **kwargs):
    """Call ``push`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().push(*args, **kwargs)


def zmq_push_multipart(*args, **kwargs):
    """Call ``push_multipart`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().push_multipart(*args, **kwargs)


def zmq_push_string(*args, **kwargs):
    """Call ``push_string`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().push_string(*args, **kwargs)


def zmq_push_raw(*args, **kwargs):
    """Call ``push_raw`` of the shared ZMQClient; see ``zprocess.ZMQClient``."""
    return ZMQClient.instance().push_raw(*args, **kwargs)


def RemoteProcessClient(host, port=None):
    """Return a ``zprocess.remote.RemoteProcessClient`` for ``host``.

    It has the security settings from LabConfig. ``port`` defaults to the labconfig's
    ``ports/zprocess_remote``.
    """
    if port is None:
        config = get_config()
        port = config['zprocess_remote_port']
    return ProcessTree.instance().remote_process_client(host, port)


def run_server(module, port, *extra_args, tui=False):
    """Run a zprocess server configured according to LabConfig.

    Runs ``python -m zprocess.<module>`` with the security settings from LabConfig.
    With ``--daemon`` on the command line the server starts in the background,
    otherwise it runs in the foreground until interrupted.

    Parameters
    ----------
    module : str
        Name of the server's module in ``zprocess``, such as ``'zlock'``.
    port : int or str
        Port for the server to listen on.
    *extra_args : str
        Further command-line arguments for the server.
    tui : bool, optional
        Whether a foreground server shows the text-based interface, unless
        ``--no-tui`` is on the command line.
    """
    # setup_logging imports this module, so LOG_PATH cannot be imported at the top:
    from labscript_utils.setup_logging import LOG_PATH

    config = get_config()
    cmd = [
        sys.executable, '-m', f'zprocess.{module}', '--port', str(port),
        *extra_args, '-l', LOG_PATH,
    ]
    if config['shared_secret_file'] is not None:
        cmd += ['--shared-secret-file', config['shared_secret_file']]
    elif config['allow_insecure']:
        cmd += ['--allow-insecure']
    else:
        cmd += ['--no-allow-insecure']

    if '--daemon' in sys.argv:
        zprocess.start_daemon(cmd)
    else:
        if tui and '--no-tui' not in sys.argv:
            cmd += ['-tui']
        try:
            subprocess.call(cmd)
        except KeyboardInterrupt:
            pass


def _ping_starting_locally(client, module):
    """Ping a server, starting ``labscript_utils.<module>`` first if the server is
    meant to run on this computer and does not answer."""
    if gethostbyname(client.host) == gethostbyname('localhost'):
        try:
            # Short timeout on localhost, so as not to waste time:
            client.ping(timeout=0.05)
        except zmq.ZMQError:
            # Not running. Start it, to run forever even after this program exits,
            # since other programs may use it. Then try again, with a longer
            # timeout to give it time to start up:
            zprocess.start_daemon(
                [sys.executable, '-m', f'labscript_utils.{module}', '--daemon']
            )
            client.ping(timeout=15)
    else:
        client.ping()


ZLOCK_DEFAULT_TIMEOUT = 45
_zlock_server_supports_readwrite = False


def connect_to_zlock_server():
    """Ping the zlock server, starting one first if it should run on this computer.

    Also records whether the server supports read-write locks, which ``Lock`` needs,
    and sets the default lock timeout to ``ZLOCK_DEFAULT_TIMEOUT`` seconds.
    """
    client = ProcessTree.instance().zlock_client
    _ping_starting_locally(client, 'zlock')

    global _zlock_server_supports_readwrite
    if hasattr(client, 'get_protocol_version'):
        version = client.get_protocol_version()
        if Version(version) >= Version('1.1.0'):
            _zlock_server_supports_readwrite = True

    # Callers can change the default later with the client's set_default_timeout:
    client.set_default_timeout(ZLOCK_DEFAULT_TIMEOUT)


_connected_to_zlog = False


def ensure_connected_to_zlog():
    """Ping the zlog server, starting one first if it should run on this computer.

    It does nothing once a ping has succeeded.
    """
    global _connected_to_zlog
    if _connected_to_zlog:
        return
    _ping_starting_locally(ProcessTree.instance().zlog_client, 'zlog')
    _connected_to_zlog = True
