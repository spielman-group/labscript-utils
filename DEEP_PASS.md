# labscript-utils deep pass

What the code-health campaign's deep pass leaves open in labscript-utils. The
file goes once these are done or recorded elsewhere.

## Upstream stage

CodeHealth carries upstream master 22616a7..f77ac19, with the floors Python 3.13,
qtutils 4.4.3 and zprocess 3.0.1. Up to a2c4901 it was ported by hand in upstream's
form; a2c4901..f77ac19 is cherry-picked with -x, as 4a51a29..afe96f2.

Not possible, the fork's code having drifted:
- 1ca6f16 (ToolPaletteGroup's linked widths), c2ae695 (AnalogInput's plot
  window), ba04ee1 (CameraServer), 44205a5 (AnalogInput's plot button tooltip)
  and 05b4301's AnalogInput part: step 4 removed that code, on Ian's word.
  It stays removed, and the removals are offered upstream when packaging starts
  (Ian, U2).
- 3df0276's connection-table diff message: step 4 removed `assert_superset`. Its
  other two parts the fork already has.
- 2e96b30's quad_driver text: step 2 made quad_driver and quad_monitor one class.
  The behaviour is upstream's.

Adapted to the TOML labconfig and app configs: 3d100b9, 701389e, 12f86ac with
0f6bf4f, 126c8c5, 516e254, 53c2544, d2d7fea, 1dcbc53, 2b100b5, and
`programs.open_file`'s TOML array arguments. 37a7450 keeps the fork's PyQt6 docs
inventory.

Fork commits on top of upstream's, on Ian's word:
- edcf752: `[gui] qt_binding` defaults to PyQt6, and PySide6 is not required.
- b4d1aff: `exec_qapplication` relies on the timer that `setup_application` starts
  since 8f07c1a, and starts none of its own.

Open:
- `excepthook.install()`: importing the module still calls it, as upstream does,
  until every program calls it.
- Offered upstream, on UpstreamBugFixes: `text_editor.open_in_editor`
  (de8754d), `assert_superset` and `Connection.diff`'s removal (2f50183), and the
  quad conversions' shared base (d35f39c).
- Ian decides whether the window-geometry pair is offered upstream.
- Fork-only, on top of upstream: the port-in-use `OSError` from `ZMQServer`, and
  `exec_qapplication`'s window deletion and `on_interrupt`.
- hyde forces Fusion and a light palette before `configure_qapplication`, whose
  `setup_application` then sets `FusionStyle` and derives item views' alternate
  row colour from that palette. hyde's owner decides what it keeps.

## Compatibility audit

Every compatibility path on CodeHealth is upstream's own form or one Ian kept,
but for the one below.
- Upstream's: `experiment_name` read as `apparatus_name`, dragdroptab's `tab_bar`,
  `setup_logging`'s ignored `maxBytes` and `backupCount`, `UnitConversion`'s
  `unit_list` and `units`, FileWatcher's two-argument callbacks, the device
  registry's deprecated decorators and `deprecated_import_alias`, bare unit
  conversion names, a connection table's missing columns read through defaults,
  `np.str_` globals, and the excepthook installed on import.
- Ian's: the INI labconfig and app-config conversion with its FutureWarning (step
  1 entries 1, 3 and 8; step 5 entry 14), and the unit conversions' full-name
  globals (step 5 entry 5).
- For Ian: the FutureWarnings the fork added on reading an old connection table
  (`connections.py`, its missing columns and bare unit-conversion names;
  `properties.py`, its `repr()` dicts). Upstream reads all three silently. The
  reading keeps old shot files working; the warnings and their "will be removed"
  markers announce dropping it.

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
- blacs's `tracelog` command-line argument imports `labscript_utils.tracelog`,
  which d3f06cb removed; upstream blacs 0a29fff removes the argument.
