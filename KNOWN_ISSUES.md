# Known issues

- `connections.py`, `ConnectionTable.remove_device`: deleting a device from the lookup table leaves its parent's child_list unchanged, so compatibility comparisons can still include a failed device (source review).
- `properties.py`, `serialise`: validation consumes generator values before the encoding traversal, serializing their contents as empty lists (source review).
- `labscript_profile/create.py`, connection-table compilation: the compile callback ignores failure and creation reports output written even after unsuccessful compilation (source review; not executed).

- `settings.py`: `Settings.load` reads each saved setting with `eval` on the HDF5 attribute text, so a hostile settings file runs code, and a malformed one loses every setting with only a print.
- `unitconversions/optotunelens.py`: with its default fit coefficients (`a`, `b`, `c` all 0), `OptotuneLens.distance_to_base` divides by zero.
- `ls_zprocess.py`: `Lock` drops `read_only` unless `connect_to_zlock_server()` has run in the process, so a process that never calls it takes an exclusive lock where it asked for a shared one.
- `qtwidgets/dragdroptab.py`: every `DragDropTabWidget` built with `group_id=None` joins the same group, so a tab can be dragged between widgets that have nothing to do with each other.
- `labscript_profile` sets the profile path to None when `getuser()` fails; then `setup_logging` raises TypeError at import, and `LabConfig` puts the string 'None' in for `%(labscript_suite)s`.
- `labconfig.py`: `load_appconfig` silently drops a top-level scalar from a hand-edited app config, since it keeps only the tables (`isinstance(section, dict)`).
- `labscript_profile/toml_config.py`: potential, unconfirmed: on Windows, `dump_toml_file` cannot replace a config that another process holds open without FILE_SHARE_DELETE, so the save raises and the old file is kept. Not tested on Windows or on the lab's network share.
- `labscript_profile/toml_config.py`: a config or globals file that `dump_toml_file` replaces takes the owner, group and ACLs that a new file in its folder gets, and keeps only its mode bits. On POSIX its ACL entries are lost and its copied group bits apply to the new group; on Windows (unconfirmed, not tested there) it takes the folder's inherited ACLs, which the temp file also has while it is written.
- `versions.py`, `package_version`: a Git worktree's `.git` file fails the directory-only checkout check, so its version falls back to installed metadata rather than identifying the imported commit (source review; inherited predicate).
- `device_registry/_device_registry.py`: if registry population fails after registering some devices, the nonempty-registry sentinel suppresses population on later lookups and can leave remaining devices undiscovered (source review; inherited failure path).
- `labscript_profile/toml_config.py`, `dump_toml_file`: its docstring promises mode 0600 for a new file, but creation uses 0666 filtered by the process umask (source review; documentation/code mismatch).
- `labscript_profile/__init__.py`, `add_userlib_and_pythonlib`: a scalar number or boolean in `userlib` or `pythonlib` raises outside the malformed-config boundary and prints an interpreter-startup traceback through the `.pth` bootstrap (source review; not executed).
