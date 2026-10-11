#####################################################################
#                                                                   #
# tracelog.py                                                       #
#                                                                   #
# Copyright 2013, Monash University                                 #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import sys
import inspect
import threading
from datetime import datetime
import traceback


def log(log_path=None, module_names=(), sub=False, all=False, mode='w'):
    """Trace and log Python execution.

    Each line of output has the time, thread name, module name, line number,
    containing function name and source line. Indentation before the thread name
    represents stack depth, and indentation before the source line is as in the
    source line itself. Tracing applies to the calling thread and to threads
    started afterwards.

    Parameters
    ----------
    log_path : str, optional
        Path of the output file to write to, or None (the default) for stdout.
    module_names : sequence of str, optional
        Names of the modules to trace.
    sub : bool, optional
        Whether to trace modules whose names begin with one of ``module_names``,
        such as their submodules. Default False.
    all : bool, optional
        Whether to trace all modules, in which case ``module_names`` is ignored.
        Default False.
    mode : str, optional
        Mode to open the output file in, if ``log_path`` is not None. Default 'w'.
    """
    if log_path is None:
        outfile = sys.stdout
    else:
        outfile = open(log_path, mode, 1)

    threadlocal = threading.local()

    def per_thread_init():
        threadlocal.stack_depth = 0
        threadlocal.threadname = threading.current_thread().name
        threadlocal.is_initialised = True

    def write(module_name, lineno, function, message):
        # Chop microseconds to milliseconds.
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        indentation = ' '*(2*threadlocal.stack_depth - 1)
        output = (
            f"[{timestamp}]{indentation}{threadlocal.threadname}: "
            f"{module_name}:{lineno} in {function}: "
        )
        if isinstance(message, list):
            indent = len(output)
            output += message[0]
            for line in message[1:]:
                output += ' '*indent + line
        else:
            output += message + '\n'

        # Atomic, thanks to the GIL, so access from multiple threads need not be
        # serialised.
        outfile.write(output)

    def traceit(frame, event, arg):
        if sys is None:
            # Interpreter is shutting down
            return
        try:
            assert threadlocal.is_initialised
        except AttributeError:
            per_thread_init()
        if event == "call":
            threadlocal.stack_depth += 1
        elif event == "return":
            threadlocal.stack_depth -= 1
        else:
            filename, lineno, function, code_context, index = inspect.getframeinfo(frame, context=1)
            try:
                module_name = frame.f_globals["__name__"]
            except KeyError:
                module_name = '<string>'
            if (module_name in module_names or all
                    or (sub and any([module_name.startswith(s) for s in module_names]))):
                line = code_context[0].rstrip() if code_context else '<within exec() or eval()>'
                if event == 'line':
                    write(module_name, lineno, function, line)
                elif event == 'exception':
                    exc_type, exc_value, _ = arg
                    exception = traceback.format_exception_only(exc_type, exc_value)
                    write(module_name, lineno, function, exception)
        return traceit

    per_thread_init()
    write('tracelog','','','\n\n***starting***\n')
    threading.settrace(traceit)
    sys.settrace(traceit)
