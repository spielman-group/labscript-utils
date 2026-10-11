# Known issues

- `settings.py`: `Settings.load` reads each saved setting with `eval` on the HDF5 attribute text, so a hostile settings file runs code, and a malformed one loses every setting with only a print.
- `unitconversions/`: 9 of the 13 conversion classes raise AttributeError when built with `calibration_parameters=None`, the default their signatures give.
- `unitconversions/optotunelens.py`: with its default fit coefficients (`a`, `b`, `c` all 0), `OptotuneLens.distance_to_base` divides by zero.
- `ls_zprocess.py`: `Lock` drops `read_only` unless `connect_to_zlock_server()` has run in the process, so a process that never calls it takes an exclusive lock where it asked for a shared one.
- `qtwidgets/dragdroptab.py`: every `DragDropTabWidget` built with `group_id=None` joins the same group, so a tab can be dragged between widgets that have nothing to do with each other.
- `labscript_profile` sets the profile path to None when `getuser()` fails; then `setup_logging` raises TypeError at import, and `LabConfig` puts the string 'None' in for `%(labscript_suite)s`.
- `labconfig.py`: `load_appconfig` silently drops a top-level scalar from a hand-edited app config, since it keeps only the tables (`isinstance(section, dict)`).
