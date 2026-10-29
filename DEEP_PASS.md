# labscript-utils deep pass

What the code-health campaign's deep pass leaves open in labscript-utils. The
file goes once these are done or recorded elsewhere.

## Upstream stage

CodeHealth carries, ported by hand, every row of upstream master 22616a7..a2c4901
that the review marked adopt, and the floors Python 3.13, qtutils 4.4.1 and
zprocess 3.0.1. Open:
- `setup_application` (upstream a98a8d7, c63b50d, 2588393, 27cc95a, 36d1dd5) is
  held. Folding it into `configure_qapplication` conflicts with lyse, which sets
  an application style sheet after `get_qapplication` has configured it, and with
  hyde, which forces Fusion and its own light palette. The fork also gives Fusion
  to macOS only, by design. Ian decides.
- Ian's call, not adopted: the labconfig logging level (516e254), lazy logging
  arguments (9c0a161), and opening files in the OS default program (4db2e74).
- Each consumer's `tests/conftest.py` must set
  `LABSCRIPT_DISABLE_GRAPHICAL_EXCEPTHOOK`, which replaced
  `LABSCRIPT_NO_ERROR_DIALOG`; lyse must shut its output box down on
  `aboutToQuit`, since `exec_qapplication` now deletes the windows.

## Waiting on a zprocess release

labscript-utils requires `zprocess>=3.0.1`.
- `ls_zprocess.ZMQServer.handler` catches `BaseException` and sends back only
  what the client can raise. Two of its lines can go once the floor holds
  zprocess 51adae8 and 6c31b8f, which no upstream release has.
- `LinkIndicator`'s docstring says it asks through a client of its own because
  two threads on one client can block each other for good. The floor now holds
  upstream's c407999, which may fix that Interruptor deadlock as the fork's
  162afe7 does; the sentence goes once that is checked. Whether the
  one-client-per-thread rule then stays is Ian's.

## Dependencies

- `pyqtgraph` can leave labscript-utils' dependencies. No labscript-utils code
  imports it, and the packages that do, runviewer, labscript-devices and
  labscript-optimization, declare it themselves.

## For Ian

- Should `device_registry` re-export `populate_registry`, `BLACS_tab_registry`
  and `ClassRegister`? Its `__all__` leaves them out, and nothing in the suite
  imports them from there.

## On merge

Every consumer's `CodeHealth` uses names that only labscript-utils' `CodeHealth`
has, so they merge together. Among them:
- blacs dee664a renames its plugin hooks to `get_event_handlers`, the only one
  `PluginManager` asks for (d515339). Merged without it, labscript-utils drops
  every BLACS plugin's event handlers.
- `dump_toml_file`'s atomic save: runmanager 520e32f, blacs 8c6455a, lyse
  82e1bdc.
- `ZMQServer`'s `server` and `default_port`: runmanager cf7cfb8, runviewer
  82ac827.
- `next_available_indexed_filepath`'s `strip_suffix`: runmanager 3f569c1.
