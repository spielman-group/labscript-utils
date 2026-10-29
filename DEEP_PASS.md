# labscript-utils deep pass

What the code-health campaign's deep pass leaves open in labscript-utils. The
file goes once these are done or recorded elsewhere.

## Waiting on a zprocess release

labscript-utils requires `zprocess>=2.18.0`.
- `ls_zprocess.ZMQServer.handler` catches `BaseException` and sends back only
  what the client can raise. Two of its lines can go once the floor holds
  zprocess 51adae8 and 6c31b8f, which no release has.
- `LinkIndicator`'s docstring says it asks through a client of its own because
  two threads on one client can block each other for good. The sentence goes
  once the floor holds a fix for that Interruptor deadlock: the fork's zprocess
  162afe7, or upstream's c407999 in zprocess 3.0.0, which has not been checked
  against it. Whether the one-client-per-thread rule then stays is Ian's.

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
