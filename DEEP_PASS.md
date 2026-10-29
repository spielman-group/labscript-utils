# labscript-utils deep pass

What the code-health campaign's deep pass leaves open in labscript-utils. The
file goes once these are done or recorded elsewhere.

## Upstream stage

CodeHealth carries upstream master 22616a7..a2c4901, ported by hand in upstream's
form, with the floors Python 3.13, qtutils 4.4.1 and zprocess 3.0.1.

Not possible, the fork's code having drifted:
- 1ca6f16 (ToolPaletteGroup's linked widths), c2ae695 (AnalogInput's plot
  window) and ba04ee1 (CameraServer): step 4 removed that code, on Ian's word.
- 3df0276's connection-table diff message: step 4 removed `assert_superset`. Its
  other two parts the fork already has.
- 2e96b30's quad_driver text: step 2 made quad_driver and quad_monitor one class.
  The behaviour is upstream's.

Adapted to the TOML labconfig and app configs: 3d100b9, 701389e, 12f86ac with
0f6bf4f, 126c8c5, 516e254, and `programs.open_file`'s TOML array arguments.

Open:
- 05560c1 and 8788417, runmanager's `globals_namespace` and `pylab_namespace`
  keys, wait for runmanager to have them (upstream runmanager #163).
- `excepthook.install()`: importing the module still calls it, as upstream does,
  until every program calls it.
- `text_editor.open_in_editor` goes once its callers use `programs.open_file`,
  upstream's form.
- Fork-only, on top of upstream: the port-in-use `OSError` from `ZMQServer`, and
  `exec_qapplication`'s window deletion and `on_interrupt`.
- hyde forces Fusion and a light palette before `configure_qapplication`, whose
  `setup_application` then sets `FusionStyle` and derives item views' alternate
  row colour from that palette. hyde's owner decides what it keeps.

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
