The *labconfig.toml* file
=========================

The `labconfig.toml` file is a global configuration file for your **labscript-suite** installation.
It contains configurable settings that govern how the individual components of the suite operate.
The file is `labconfig/<hostname>.toml` in the profile directory, where `<hostname>` is the host name of the computer.
The profile directory is `~/labscript-suite`, or the directory named by the environment variable `LABSCRIPT_SUITE_PROFILE` if it is set.
On macOS, the host name is the output of `scutil --get LocalHostName`; on Windows and Linux, it is the value of Python's `socket.gethostname()`.
For example, on a computer with the host name `heisenberg`, the file is `~/labscript-suite/labconfig/heisenberg.toml`.

When :doc:`installing the labscript suite for the first time <labscript-suite:installation/index>`,
the `labscript-profile-create` command creates the `labscript-suite` profile directory and a labconfig file for the computer.
Importing `labscript_utils`, as the applications of the suite do, also creates them if the `labscript-suite` directory does not exist.
To change the configuration of the installation, edit the labconfig file.

The labconfig file of a new profile
-----------------------------------

`labscript-profile-create` makes the labconfig file of a new profile from the file below, `labscript_profile/default_profile/labconfig/example.toml`.
In the new file, it replaces each backslash with the path separator of the platform, sets `[security]` `shared_secret` to a new key file, and sets `apparatus_name` to the name given with the `--apparatus_name` option, if there is one.
On Linux and macOS, it also sets `shared_drive` to `$HOME/labscript_shared` and sets `text_editor` and `hdf5_viewer` to empty values.

.. note::

	When a release of the suite adds keys to this file, existing labconfig files are not changed.
	The applications use the default of each key that is missing from a labconfig file, as given in the list of keys below.
	To change the value of a key that is missing, add the key to your labconfig file.

.. include:: ../../labscript_profile/default_profile/labconfig/example.toml
	:code:

Values
------

Values are TOML strings, booleans, numbers or arrays.
A string is written in single quotes, so that the backslashes of a Windows path are not escapes.
A string can refer to another key in the same section or in the `[default]` section as `%(key)s`.
The `labscript_suite` key is always defined, and is the path of the `labscript-suite` profile directory.
Environment variables in a string are expanded, as `$NAME` on all platforms or as `%NAME%` on Windows.
A literal `%` is written `%%`, so a Windows environment variable is written `%%NAME%%`.
The keys of the `[default]` section are also available in every other section, so that, for example, `[paths]` `experiment_shot_storage` is the same as `[default]` `experiment_shot_storage`.
Section and key names are not case sensitive.

The default of a key, as given below, is the value that the applications use when the key is missing from the labconfig file.
It can differ from the value in the labconfig file of a new profile: for example, a new profile has `[runmanager]` `pylab_namespace` set to `false`, and the default is `true`.
A key that is listed below as required has no default, and the applications that read it do not start if it is missing.

Keys
----

`[default]`
^^^^^^^^^^^

`apparatus_name`
    The name of the apparatus.
    It must be a valid Python identifier, because it is the name of a package under `labscriptlib`.
    The other paths in the labconfig file of a new profile contain it.
    Required by BLACS, lyse, runmanager and runviewer.
    The deprecated name `experiment_name` is read as `apparatus_name`, with a warning, and setting both is an error.

`shared_drive`
    The directory where this computer mounts the drive that is shared between the computers of the installation.
    The applications send the paths of shot files to each other relative to this directory, so it may be mounted at a different path on each computer.
    On Linux and macOS, `labscript-profile-create` sets it to `$HOME/labscript_shared`.
    Required by BLACS, lyse, runmanager and runviewer.

`experiment_shot_storage`
    The directory in which runmanager creates shot files.
    The shot files of an experiment script are in the subdirectory named after the script, in the subdirectory given by `[runmanager]` `output_folder_format`.
    The applications also open their shot file dialogs in this directory.
    Required by BLACS, lyse, runmanager and runviewer.

`userlib`, `pythonlib`
    Lists of directories, comma-separated in a string or as a TOML array, that are added to the Python module search path of every Python interpreter in the environment that the suite is installed in.
    BLACS also opens its unit conversion file dialogs in `userlib`.
    If a key is missing, nothing is added for it.

`labscriptlib`
    The directory of the experiment scripts.
    runmanager opens its experiment script file dialog in this directory.
    Required by runmanager.

`analysislib`
    The directory of the lyse analysis routines.
    lyse opens its analysis routine file dialog in this directory.
    Required by lyse.

`app_saved_configs`
    The directory of the saved configurations of the applications, with a subdirectory for each of `blacs`, `lyse`, `runmanager` and `runviewer`.
    BLACS keeps its front panel settings in its subdirectory, in a file named after the computer.
    runmanager, lyse and runviewer keep their default configuration files, `runmanager.toml`, `lyse.toml` and `runviewer.toml`, in theirs.
    Required by BLACS.
    The default for the other applications is `%(labscript_suite)s/userlib/app_saved_configs/%(apparatus_name)s`.

`user_devices`
    A list of the names of importable packages that contain labscript devices, in addition to `labscript_devices`, comma-separated in a string or as a TOML array.
    The default is `user_devices`.

`[paths]`
^^^^^^^^^

`connection_table_h5`
    The compiled connection table, which BLACS loads when it starts.
    Required by BLACS.

`connection_table_py`
    The connection table script, which BLACS opens in the text editor, and compiles to `connection_table_h5` when the user recompiles the connection table.
    Required by BLACS.

`[servers]`
^^^^^^^^^^^

`zlock`
    The host name of the computer that runs the zlock server, which manages file locks for all computers of the installation.
    If the host is the local computer and no zlock server is running, the first application that needs one starts it.
    Required by all the applications.

`runmanager`
    The host name of the computer that runs runmanager.
    BLACS asks it for shots, and the `runmanager.remote` client sends it commands.
    The default is `localhost`.

`blacs`
    The host name of the computer that runs BLACS.
    runmanager asks it for the status of BLACS.
    The default is `localhost`.

`lyse`
    The host name of the computer that runs lyse.
    runmanager sends completed shot files to it.
    The default is `localhost`.

`[ports]`
^^^^^^^^^

`blacs`
    The port on which BLACS answers requests for its status.
    runmanager sends them to this port on the host given by `[servers]` `blacs`.
    Required by BLACS.
    The default for the other applications is 42517.

`lyse`
    The port on which lyse receives shot files and requests for its dataframe, such as `lyse.data`.
    runmanager sends completed shot files to this port on the host given by `[servers]` `lyse`.
    Required by BLACS, lyse and runmanager.
    The default for `lyse.data` is 42519.

`runviewer`
    The port on which runviewer receives shot files.
    runmanager sends shot files to this port on the local computer.
    Required by runmanager.
    The default for runviewer is 42521.

`runmanager`
    The port of the runmanager server.
    BLACS sends its requests for shots to this port on the host given by `[servers]` `runmanager`, and so does the `runmanager.remote` client.
    The default is 42523.

`zlock`
    The port of the zlock server.
    The default is 7339.

`zlog`
    The port of the zlog server, which writes the log files of the applications and their subprocesses to the `logs` directory of the `labscript-suite` profile directory.
    The zlog server runs on the computer of the top-level process, so there is no `[servers]` entry for it.
    If it is not running, the first application that needs it starts it.
    The default is 7340.

`zprocess_remote`
    The port on which the zprocess remote server listens.
    This server is started by `python -m labscript_utils.remote`, and runs BLACS device workers on another computer.
    BLACS connects to the port of the `RemoteBLACS` device in the connection table, which is 7341 by default.
    The default is 7341.

`[timeouts]`
^^^^^^^^^^^^

`communication_timeout`
    The timeout, in seconds, of the requests that one application sends to another, such as the requests of BLACS to runmanager and those of the `runmanager.remote` client.
    A client created with a timeout of its own does not use it.
    BLACS allows this long for runmanager to choose and prepare a shot.
    The default is 60.

`liveness_timeout`
    The time, in seconds, that BLACS waits for runmanager to answer the question of whether it is there, which BLACS asks before each exchange of shots.
    The default is 5.

`[programs]`
^^^^^^^^^^^^

`text_editor`, `text_editor_arguments`
    The program that opens the experiment script in runmanager, the analysis routines in lyse and the connection table script in BLACS, and its arguments.
    The arguments are separated by spaces in a string, or are a TOML array, and the argument `{file}` is replaced by the path of the file.
    If no argument contains `{file}`, the path is the first argument.
    If `text_editor` is empty, the file is opened for editing in the operating system's default program: on Windows, the program of the "Edit" action of the file type, or Notepad if the file type has none; on macOS, the default text editor; on Linux, the default program of the file type, with `xdg-open`.
    New profiles have the path of VS Code from its user installer on Windows, `%%LOCALAPPDATA%%\Programs\Microsoft VS Code\Code.exe`, and an empty `text_editor` on Linux and macOS.
    The system installer of VS Code puts it in `%%PROGRAMFILES%%\Microsoft VS Code\Code.exe`.
    If the program cannot be started, the application shows a dialog that says so.

`hdf5_viewer`, `hdf5_viewer_arguments`
    The program that opens shot files from lyse, and its arguments, in the same form as `text_editor_arguments`.
    If `hdf5_viewer` is empty, the file is opened in the operating system's default program for `.h5` files.
    New profiles have the path of HDFView from its Windows installer, `%%LOCALAPPDATA%%\HDFView\HDFView.exe`, on Windows, and an empty `hdf5_viewer` on Linux and macOS.
    `HDFView <https://github.com/HDFGroup/hdfview/releases>`_, from The HDF Group, is a viewer for HDF5 files.
    On Windows, its installer also makes it the default program for `.h5` files.
    If the program cannot be started, lyse shows a dialog that says so.


`[labscript]`
^^^^^^^^^^^^^

`save_hg_info`, `save_git_info`
    Whether to save Mercurial or Git information about the files under `labscriptlib` that are saved in each shot file.
    For Mercurial, this is the output of `hg log --limit 1`, `hg status` and `hg diff` for the file.
    For Git, this is the output of `git branch --show-current`, `git describe --tags --always HEAD`, `git rev-parse HEAD` and `git diff HEAD` for the file.
    The output is saved in attributes of the copy of the file in the shot file.
    The default is `false`.

`["blacs/plugins"]`
^^^^^^^^^^^^^^^^^^^

The section name and the two `connection_table.` keys contain characters that TOML does not allow in a bare key, so they are written in quotes.

`connection_table`, `cycle_time`, `delete_repeated_shots`, `general`, `memory`, `progress_bar`, `theme`
    Whether to load the BLACS plugin of the same name.
    The default is `true` for `connection_table`, `general` and `theme`, and `false` for the others.
    A package can register further plugins in the `blacs.plugins` entry point group, and a key of the same kind switches each of them on or off.
    Such a plugin is not loaded unless its key is `true`.

`"connection_table.hashable_types"`
    An array of file extensions.
    The connection table plugin detects changes to the files that it watches by their MD5 checksums for files with these extensions, and by their modification times for other files.
    When all the watched files have their previous contents again, the plugin removes its recompile notification.
    It detects this only if all the modified files have these extensions.
    The default is `['.py', '.txt', '.ini', '.toml', '.json']`.

`"connection_table.polling_interval"`
    The interval, in seconds, at which the connection table plugin checks the files that it watches.
    The default is 1.

`[gui]`
^^^^^^^

`color_scheme`
    The colour scheme of BLACS, lyse, runmanager and runviewer: `system`, `light` or `dark`.
    With `system`, the applications use the colour scheme of the operating system.
    The key applies with Qt 6.8 or later.
    On Linux, `light` and `dark` take effect only with a Qt platform theme that supports them, such as the GTK platform theme.
    The default is `system`.

`qt_binding`
    The Qt binding of BLACS, lyse, runmanager and runviewer: `PySide6` or `PyQt6`.
    The `pyqt` extra of the labscript-suite package installs PyQt6. To use PySide6, install it in the Python environment of the labscript suite yourself.
    PyQt5 is not supported.
    If the environment variable `QT_ENV` is set, it takes precedence over this key.
    The default is `PyQt6`.

`[lyse]`
^^^^^^^^

`autoload_config_file`
    A lyse configuration file that lyse loads when it starts.
    The analysis routines store the sizes and positions of their plot windows in the same directory.
    By default, lyse loads no configuration file, and the plot window settings are in the `lyse` subdirectory of `app_saved_configs`.

`integer_indexing`
    Whether the rows of the lyse dataframe are indexed by sequence index, run number and run repeat.
    Otherwise they are indexed by sequence and run time.
    The default is `false`.

`["lyse/plugins"]`
^^^^^^^^^^^^^^^^^^

The section name contains a character that TOML does not allow in a bare key, so it is written in quotes.

`delete_repeated_shots`
    Whether to load the lyse plugin of the same name.
    The default is `false`.
    A package can register further plugins in the `lyse.plugins` entry point group, and a key of the same kind switches each of them on or off.
    Such a plugin is not loaded unless its key is `true`.

`[runmanager]`
^^^^^^^^^^^^^^

`autoload_config_file`
    A runmanager configuration file that runmanager loads when it starts.
    `labscript-profile-create` writes this file, so that runmanager opens the example experiment the first time it runs.
    By default, runmanager loads no configuration file.

`output_folder_format`
    The subdirectory of the shot files of a sequence, relative to the experiment script's directory in `experiment_shot_storage`.
    It is formatted with `strftime` and the time of the sequence, and then with the fields `{sequence_index}`, `{sequence_timestamp}`, `{sequence_date}`, `{sequence_id}`, `{script_basename}` and `{globals[name]}`, which is the value of the global `name` in each shot.
    A field can have a format specification, as in `{sequence_index:04d}`.
    Each `%` of a `strftime` code is written `%%`.
    If the key is missing, the format is `%Y/%m/%d/{sequence_index:05d}`, with the path separator of the platform.

`filename_prefix_format`
    The start of the names of the shot files of a sequence, in the same form as `output_folder_format`.
    runmanager adds the run number and `.h5` to it.
    If the key is missing, the format is `{sequence_timestamp}_{script_basename}`.

`globals_namespace`
    A Python file that runmanager runs each time it evaluates globals.
    The names in the file's `__all__`, or if it has none, the names that do not start with an underscore, are available to the expressions of the globals.
    If the file cannot be run, every global holds the error.
    By default, there is no such file.

`pylab_namespace`
    Whether the names of `from pylab import *` are available to the expressions of the globals.
    Runmanager will stop providing these names in a future version, and warns about each global that uses them.
    The default is `true`; new profiles set it to `false`.

`[security]`
^^^^^^^^^^^^

`shared_secret`
    The path of the key file that encrypts and authenticates the communication between the applications.
    All computers of the installation must use copies of the same key file.
    `labscript-profile-create` creates a key file and sets this key.

`allow_insecure`
    Whether the applications communicate without encryption when `shared_secret` is not set.
    The applications do not start if neither key is set.
    The default is `false`.

`[logging]`
^^^^^^^^^^^

`level`
    The level of the log messages that the applications and their subprocesses record: `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`, or `off`.
    With `off`, the applications record no log messages, to the log files or to the terminal, and start no zlog server, and the zlock and zprocess remote servers that `labscript_utils.zlock` and `labscript_utils.remote` start log nothing.
    Warnings are then printed as Python normally does.
    The default is `DEBUG`.

`maxBytes`
    The size, in bytes, at which the zlog server starts a new log file.
    The default is 52428800, which is 50 MiB.

`backupCount`
    The number of previous log files that the zlog server keeps for each log.
    The default is 1.
