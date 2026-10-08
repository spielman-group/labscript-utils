"""Tests for the graphical error dialog's opt-out.

This is the switch every test run in the suite depends on to stay silent, and
getting it wrong is invisible from inside the code: the failure mode is a dialog
that does not appear when someone asked for one, or windows appearing during a
test run that was supposed to be quiet.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import labscript_utils.excepthook as excepthook


def test_labscript_no_error_dialog_1_suppresses_the_dialog_and_unset_does_not():
    # The variable is read once, when excepthook imports, so each case needs a
    # fresh process.
    for value, suppressed in [('1', 'True'), (None, 'False')]:
        environ = dict(os.environ)
        environ.pop('LABSCRIPT_NO_ERROR_DIALOG', None)
        if value is not None:
            environ['LABSCRIPT_NO_ERROR_DIALOG'] = value
        result = subprocess.run(
            [
                sys.executable,
                '-c',
                'import labscript_utils.excepthook as e; print(e.NO_ERROR_DIALOG)',
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=environ,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == suppressed, value


class TestTheFlagIsReadWhenUsed(object):
    """The documented escape hatch is assigning to the module attribute."""

    def test_assigning_no_error_dialog_switches_the_error_dialog_on_and_off(self):
        """A test *of* the dialog sets NO_ERROR_DIALOG and gets a dialog.

        This is the case the environment variable deliberately cannot express,
        so it has to keep working. If someone captures the flag at import, or
        hoists the read out of ``tkhandler``, this fails.

        ``reraise=False`` keeps sys.__excepthook__ from printing the traceback,
        and the whole subprocess module is stood in for rather than its Popen
        attribute patched, so nothing here can spawn a window.
        """
        spawned = []

        class FakePopen(object):
            def __init__(self, *args, **kwargs):
                spawned.append(args)

            def poll(self):
                return None

        class FakeSubprocess(object):
            Popen = FakePopen

        saved_flag = excepthook.NO_ERROR_DIALOG
        saved_subprocess = excepthook.subprocess
        saved_children = list(excepthook.child_processes)
        saved_logger = excepthook.l.logger
        excepthook.subprocess = FakeSubprocess
        excepthook.l.logger = None
        try:
            excepthook.NO_ERROR_DIALOG = True
            excepthook.tkhandler(ValueError, ValueError('quiet'), None, reraise=False)
            assert spawned == [], 'suppressed, so nothing should be spawned'

            excepthook.NO_ERROR_DIALOG = False
            excepthook.tkhandler(ValueError, ValueError('loud'), None, reraise=False)
            assert len(spawned) == 1, 'the dialog was asked for and not shown'
        finally:
            excepthook.subprocess = saved_subprocess
            excepthook.NO_ERROR_DIALOG = saved_flag
            excepthook.child_processes[:] = saved_children
            excepthook.l.logger = saved_logger
