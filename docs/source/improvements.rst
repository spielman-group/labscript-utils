Possible improvements
=====================

* Runviewer's channel list, lyse's routine lists and runmanager's axes are reordered with up, down, top and bottom buttons, which modern interfaces have replaced with drag and drop; all three call :meth:`labscript_utils.qtwidgets.leftclick.MovableRowsMixin.move_selected_rows`, so the change can be made in one place.

Compatibility retained
----------------------

These interfaces keep existing scripts, calibration modules and saved files working:

* INI labconfigs and application configurations are converted to TOML, with a
  warning. The old ``experiment_name`` labconfig key is read as ``apparatus_name``.
  See :doc:`labconfig`.
* Old connection-table columns, bare conversion names, property dictionaries stored
  as Python representations and NumPy string globals remain readable.
* Unit conversions retain fully qualified names, ``unit_list`` and ``units`` aliases,
  and the ``copy`` and ``math`` names exposed through star imports.
* Device-registry decorators and deprecated import aliases remain available to
  existing device modules.
* FileWatcher retains two-argument callbacks, ``modified_times`` and
  ``get_modified_times``. Logging retains the ignored ``maxBytes`` and
  ``backupCount`` arguments, and draggable tab widgets retain ``tab_bar``.
* Importing ``labscript_utils.excepthook`` still installs its handler, as upstream
  does. Removing that side effect requires checking the programs and scripts that
  depend on it.

Maintainer follow-ups
---------------------

* Decide whether the fork's warnings about old connection-table columns, bare
  conversion names and Python-representation property dictionaries should remain.
  The readers themselves remain supported.
* Reassess the exception-normalization fallbacks in
  ``labscript_utils.ls_zprocess.ZMQServer.handler`` when the declared zprocess floor
  includes upstream fixes ``51adae8`` and ``6c31b8f``. A fix available only on a fork
  does not establish that floor.
* Check upstream zprocess ``c407999`` against the fork's ``162afe7`` before revising
  LinkIndicator's explanation of cross-thread client deadlock. Whether the
  one-client-per-thread policy should change remains a separate decision.
* Decide whether ``populate_registry``, ``BLACS_tab_registry`` and ``ClassRegister``
  should be public exports of ``labscript_utils.device_registry``; its current
  ``__all__`` omits them.
* Hyde's owner must decide whether its forced Fusion style and light palette should
  remain alongside the shared ``configure_qapplication`` styling.
