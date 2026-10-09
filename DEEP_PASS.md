# labscript-utils deep pass

A planning document for step 2 of the code-health campaign, the deep pass
(`issues/code_health_campaign.md` in the meta repo). It lists candidates for
Ian's review, one section per sub-step, and is deleted when the pass is done.
Nothing is removed until Ian has reviewed each entry.

## Step 1: behaviour no one asked for

Each entry is behaviour that `CodeHealth` adds over `master` for which no
request was found, or only part of one, which the entry says. Line numbers are
`CodeHealth` at 28c5fa1. "Core lines" counts the non-blank lines the behaviour
holds, docstrings and comments included; where the proposal replaces it, the
replacement's size is given.

How the three pieces of evidence were gathered:

- **Not upstream.** The file or line is absent from `master`, and
  `git log -S'<code>' -- <file>` names the commit that added it.
- **Request.** The adding commit's message; `git -C .. log --all -S'<term>'` in
  the meta repo; and a grep of the meta repo's `issues/*.md` and `CODEX.md`.
  "None found" means only that these show no ask. The meta repo's history starts
  on 2026-04-28 (c105f41), after the TOML work (March), the shot queue (March
  and April) and the plugin framework (April 24 to 26). For those, the commit
  messages, mostly bare subjects, are the only record from the time.
- **Callers.** `git -C <repo> grep` over every file, tests included, of blacs,
  runmanager, lyse, runviewer, labscript, labscript-devices,
  labscript-optimization, labscript-agents and labscript-suite at
  `Development`, and hyde at `HEAD`. Each search was run beside a control that
  matches. "No caller" means none in these repos: a lab-local plugin or script
  outside them cannot be searched.

Three documents describe some of this code after it was written. They are cited
where they match, as descriptions, not requests; Ian decides whether any counts
as one.

- `issues/plugin_refactor_prd.md` in the meta repo (c105f41, 2026-04-28). It
  says the change "has already landed in `Production`". Its user stories 12 and
  13 say malformed plugin declarations are "logged and skipped" and deprecated
  hooks "warned on use".
- `CODEX.md`, whose `toml` entry calls the INI paths "migration only".
- `RunmanagerQueue.md` in labscript-suite (8fcb362, 2026-03-17), a plan written
  for a main agent and workers. Its extraction scope for the shot queue is
  "drag/drop, add/delete/clear/reorder, selection handling, queue
  serialization".

All 16 tests marked "Step 2.1" in `CONTRACT.md`, since deleted, are covered.
Eight are in entries 5 (two tests), 6, 7, 14, 15 and 20 (one test), 25 and
34. Seven test the base `MenuContext.render` and one
`PluginManager.get_callbacks`; both go at step 4.

### 1. An INI labconfig is converted to TOML at every interpreter start

- Where: `labscript_profile/__init__.py`: `legacy_labconfig_path`,
  `ensure_labconfig`, `_example_labconfig_data`, `_coerce_legacy_value`,
  `_convert_legacy_labconfig` (lines 50-55, 80-172, and the import at 5);
  `labscript_profile/create.py:make_labconfig_file` (10, 51-53);
  `labscript_utils/labconfig.py:LabConfig.__init__` (23, 130-131).
- Core lines: 103.
- What it does: when `<host>.toml` is missing and `<host>.ini` exists, it writes
  a TOML labconfig from the INI, typed from `example.toml`. It runs from
  `add_userlib_and_pythonlib`, which `labscript-suite.pth` calls at every Python
  start, and from every `LabConfig()`. `labscript-profile-create` refuses to run
  when only an INI exists.
- Not upstream: dee0033 "Migrate shared config handling to TOML" (2026-03-19).
- Request: none found. Searched dee0033 (no body), and the meta repo for
  `ensure_labconfig`, `_convert_legacy_labconfig` and `legacy INI`. CODEX.md's
  `toml` entry and labscript-suite's `docs/source/setup/configuration.rst:28`
  describe it as a temporary migration path. The code itself is marked
  "DEPRECATED CODE, WILL BE REMOVED".
- Callers: `ensure_labconfig` and `legacy_labconfig_path` appear only in
  labscript-utils (control: `backup_legacy_config` is found in lyse). It is
  reached on any machine whose labconfig is still `<host>.ini`; the repos cannot
  say whether one is.
- Removal user-visible: yes, on a machine with only `<host>.ini`: the apps
  would stop for want of a labconfig.
- Proposed: remove, once Ian confirms that no lab machine has only an INI
  labconfig. Both callers use `default_labconfig_path()`.
- Step: 1, possibly 4.
- Outcome: kept. Ian: INI files are converted to TOML at once, with no user
  intervention, and many labs still have them.

### 2. ShotQueueWidget as a list of shot files kept by path

- Where: `labscript_utils/qtwidgets/shotqueue.py`: `_normalise_extensions`; the
  `filesAdded` signal; the `accepted_extensions`, `allow_duplicates`,
  `column_title` and `connect_delete_requested` arguments; `files`,
  `select_paths`, `set_files`, `append`, `prepend`, `remove_selected`, `clear`,
  `is_in_queue`, `_create_row`, `_prepare_paths` and `_is_accepted_path` (lines
  65-70, 165, 170-186 in part, 224-225, 235-239, 266-296, 317-330, 349-356,
  439-456).
- Core lines: 87.
- What it does: lets the widget hold shot files by path. It adds, prepends,
  replaces, removes the selected rows, clears, and selects or looks up a file
  by path. It skips files that are missing, already queued or of the wrong
  extension.
- Not upstream: 276eba7 "Extract reusable shot queue widget" (2026-03-17); the
  arguments came in 5876c9b and c515061 (2026-04-06), and the single-string
  extension in cbbcc4f. The behaviour is ported from upstream BLACS's
  `experiment_queue.py`; that queue has since moved to runmanager.
- Request: none found. Searched the meta repo for `allow_duplicates`,
  `column_title`, `is_in_queue`, `prepend` and `select_paths`. The
  labscript-suite plan names "add/delete/clear/reorder". CODEX.md's
  RunmanagerControl audit defends the inherited methods because they read the
  row format; this entry leaves the row format alone.
- Callers: the only subclass is runmanager's `RunmanagerQueueWidget`. It calls
  `set_row_infos`, `selected_ids` and `select_ids`, and none of these methods; it
  moved from paths to row identities in f3b60db (2026-09-01). An offscreen trace
  of the real runmanager widget ran none of them. A search of all repos found the
  names only in `shotqueue.py`, which was the control.
- Removal user-visible: no. Entries 2, 4, 10, 17, 19, 21 and 22 were cut
  together in a scratch copy. labscript-utils' shot-queue tests (3) and
  runmanager's `tests/test_queueing.py` (62) still pass.
- Proposed: remove. runmanager's owner then drops three keyword arguments
  (`accepted_extensions=`, `allow_duplicates=`, `connect_delete_requested=False`)
  and `column_titles` becomes required.
- Step: 1, possibly 4.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 3. Loading an INI app config writes a TOML file and renames the INI

- Where: `labscript_utils/labconfig.py`: `APPCONFIG_SUFFIXES` (198-199),
  `_resolve_appconfig_load_path` (217-226), `backup_legacy_config` (232-247),
  `_load_legacy_appconfig_value` (276-284), the `.ini` branch of
  `load_appconfig` (312-336), and the `literal_eval` import (16).
- Core lines: 60.
- What it does: a user can load `x.ini`, or load `x.toml` when only `x.ini`
  exists. Either way it reads the INI, writes `x.toml` beside it, and renames the
  INI to `x.ini.old`.
- Not upstream: dee0033 (2026-03-19); the rename in c172cae "Prefer canonical
  TOML over stale legacy app configs" (2026-03-21); the suffix list in 7f3fc69
  (2026-08-28).
- Request: none found. Searched the three messages, and the meta repo for
  `backup_legacy_config` and `APPCONFIG_SUFFIXES`. CODEX.md describes it as
  "for migration only".
- Callers: a user reaches it. runmanager (`__main__.py:4403`), lyse
  (`__main__.py:358`) and runviewer (`__main__.py:415, 679`) offer `*.ini` in
  their file dialogs. lyse imports `backup_legacy_config`
  (`analysis_subprocess.py:50`). runviewer's
  `tests/test_save_channel_config_dialog.py:226-232` pins the `.ini` suffix.
  Nothing anywhere writes INI.
- Removal user-visible: yes, for anyone who still has a saved `.ini` app
  config.
- Proposed: remove it in the same round as the changes in lyse, runmanager and
  runviewer, made by their owners. `_resolve_appconfig_load_path` then matches
  `_resolve_appconfig_save_path` (step 2).
- Step: 1, possibly 4.
- Outcome: kept, for the reason given at entry 1.

### 4. Dropping shot files onto the shot queue

- Where: `shotqueue.py`: in `ShotQueueTreeView`, the drag set-up in `__init__`
  (77, 81, 84-88), `accepted_extensions` and `set_accepted_extensions` (94-98),
  `dragEnterEvent`, `dragMoveEvent` and `dropEvent` (118-140), and the URL
  helpers (142-158); `ShotQueueWidget`'s `connect_files_dropped` argument (178)
  and its connection (226-227).
- Core lines: 50.
- What it does: a user drops `.h5` files on the list, and the files are added
  and selected. The view also starts in Qt's drag-to-move mode.
- Not upstream: 276eba7 (2026-03-17); the argument in c515061 (2026-04-06).
  Upstream BLACS's queue accepted drops.
- Request: none found beyond the labscript-suite plan ("drag/drop"). Searched
  the meta repo for `filesDropped`, `drag and drop`, `drag-drop` and
  `drag/drop`.
- Callers: runmanager, the one consumer, turns it off. It passes
  `connect_files_dropped=False` and switches off drops and dragging
  (`queueing.py:165-170`), and has done so since 208d130 (2026-03-25).
  `filesDropped` has no consumer, and no drop handler ran in the trace.
- Removal user-visible: no; no queue in the suite accepts drops today.
- Proposed: remove. runmanager drops its four switch-off lines and the
  argument.
- Step: 1, possibly 4.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 5. Old and new plugin hooks: which one is used, and deprecation warnings

- Where: `labscript_utils/plugins.py`: `PluginManager._get_plugin_event_handlers`
  (1556-1591), the `get_menu_class` warning in `PluginManager.setup_plugins`
  (1236-1243), `_log_once` (646-651), and `_logged_plugin_warnings` (1137).
- Core lines: 46. The replacement is about 6.
- What it does: a plugin's event handlers come from `get_event_handlers` when
  its class defines that, and otherwise from `get_callbacks`. A WARNING is logged
  once per plugin in three cases: it uses `get_callbacks`; it defines both hooks;
  or its `get_menu_class` returns a class. A default BLACS start logs four of
  these warnings, and nine with every plugin enabled.
- Not upstream: dd8664f "Final revision." (2026-04-26); blacs master called
  `get_callbacks()` and logged nothing.
- Request: none found before the code. The PRD (story 13 and its decisions)
  asks for deprecated hooks to be "warned on use", and for the modern hook to
  win, with a warning, when both are defined. Against that, slice 11 of
  `issues/blacs_issues_2026_08_28.md` says the warnings "train operators to
  ignore warnings", and plans to rename the hooks in blacs instead.
- Callers: all 7 blacs plugins define only `get_callbacks`; hyde's define only
  `get_event_handlers`. No plugin in any repo defines both, so that branch is
  reached by nothing. The warnings fire at every BLACS start.
- Removal user-visible: yes, in the log only. Every real plugin gets the same
  handlers in the same order; this was checked with blacs-shaped and hyde-shaped
  plugin sets in a scratch copy.
- Proposed: use `get_event_handlers` if the plugin has it, and `get_callbacks`
  otherwise. Drop the warnings and `_log_once`. Doing slice 11 instead would
  silence the warnings without removing them.
- Step: 1.
- Outcome: removed in 4ac2114, with no warnings left. 23571b2 then asks for
  `get_callbacks` first, since `BasePlugin` forwards it to `get_event_handlers`;
  asking for `get_event_handlers` first hid a subclass overriding only the old
  name.

### 6. BasePlugin's do-nothing versions of BLACS's hooks

- Where: `plugins.py:BasePlugin`: `self.menu` and `self.notifications` in
  `__init__` (714-715), `get_notification_classes` (730-738),
  `get_setting_classes` (740-747), `set_menu_instance` (798-800),
  `set_notification_instances` (802-804), `get_save_data` (836-843), `close`
  (855-861).
- Core lines: 36.
- What it does: gives a `BasePlugin` subclass no notifications, no settings
  pages, no saved state and no clean-up, and keeps the menu and notification
  instances handed back. All of it serves `setup_plugins` and `close_plugins`.
- Not upstream: 465943d "Add shared plugin framework" (2026-04-24). Upstream
  blacs has no base class.
- Request: none found before the code; the PRD records that BasePlugin
  "should advertise no-op hooks". Searched the meta repo for `BasePlugin`.
- Callers: the only `BasePlugin` subclass is hyde's `HydePlugin`, and hyde never
  calls `setup_plugins` or `close_plugins`; it calls `instantiate_plugins`,
  `register_context`, `collect_services`, `setup_contexts`, `setup_complete` and
  `get_event_handlers`. blacs drives those hooks on its 7 plugins, which are
  `class Plugin(object)`.
- Removal user-visible: no.
- Proposed: remove. BasePlugin keeps what hyde reaches: `__init__`,
  `get_event_handlers`, `get_ui_contributions`, `get_menu_contributions` and
  `get_services`.
- Step: 1, possibly 4.
- Outcome: removed in 0e5eafe.

### 7. Checks on plugin UI and menu contributions in setup_contexts

- Where: `plugins.py:PluginManager.setup_contexts` (1326-1345, 1350-1353,
  1361-1366, 1369-1374).
- Core lines: 34. The replacement is one `try` around each `add` call.
- What it does: logs and skips a UI contribution that is not a dict, has no
  `context`, or names a context the application never registered. It also skips
  a menu contribution when no `menus` context exists, or when it is not a dict.
  Each case gets its own message.
- Not upstream: 3cef7b3 "More generalized plugins." (2026-04-25).
- Request: none found before the code; PRD story 12 says malformed
  contributions are logged and skipped. Searched the meta repo for
  `setup_contexts`.
- Callers: hyde is the only caller. It registers `menus` and `mdi` before
  routing, and its one UI contribution names `mdi`; blacs registers no context.
  The non-dict menu check is repeated in `MenuContext.render` and in hyde's
  `HydeMenuContext.render`.
- Removal user-visible: no. In a scratch copy, every malformed shape is still
  logged and skipped by the existing `except`, with a traceback in place of the
  specific message, and the good plugin is still routed. The `context` lookup
  must sit inside the `try`, or a bad item escapes.
- Proposed: simplify to one `try`/`logger.exception` around each `add` call.
- Step: 1.
- Outcome: removed in 1e0d90e; one `try` around each context's `add`.

### 8. An INI labconfig passed to LabConfig is read with a warning

- Where: `labscript_utils/labconfig.py:LabConfig._read_path` (177-195) and
  `LabConfig.DuplicateSectionError` (115);
  `labscript_profile/toml_config.py:TomlConfigParser._normalize_loaded_sections`
  (67-85) and `TomlConfigParser.read` (145-148).
- Core lines: 34.
- What it does: given a path ending `.ini`, `LabConfig` warns that INI is
  deprecated, reads the file with ConfigParser, and folds the section names to
  lower case. Any other suffix but `.toml` raises.
- Not upstream: dee0033 (2026-03-19); 806fab5 "Normalize labconfig TOML section
  names" (2026-03-19).
- Request: none found. Searched both messages, and the meta repo for
  `INI labconfig support` and `_normalize_loaded_sections`.
- Callers: none in the suite. Every `LabConfig(...)` call passes either
  `required_params` or a `.toml` path. A `<host>.ini` is converted by entry 1
  before this code runs. It is reached only by a user's own script calling
  `LabConfig('x.ini')`.
- Removal user-visible: only for such a script.
- Proposed: remove; `_read_path` reads TOML, and `LabConfig` inherits
  ConfigParser's `read`.
- Step: 1, possibly 4.
- Outcome: kept, for the reason given at entry 1.

### 9. Checks on malformed plugin setup activities

- Where: `plugins.py:PluginManager.setup_complete` (1455-1491).
- Core lines: 33.
- What it does: logs and skips a `get_setup_activities` result that is not a
  list, an item that is not a mapping, an item missing `name`, `priority` or
  `action`, and an `action` that cannot be called.
- Not upstream: 57c889f "Add ordered plugin setup activities" (2026-05-11).
- Request: none found. Searched 57c889f and the meta repo for `setup_activit`;
  the PRD predates the feature.
- Callers: only hyde's `HydePlugin` and `kernel_runtime` define
  `get_setup_activities`. Both return list literals of complete dicts with bound
  methods. blacs defines none.
- Removal user-visible: no. In a scratch copy, each bad shape still ends in a
  logged error, and the good plugin's activities still run. The difference: one
  bad item now skips the rest of that plugin's list.
- Proposed: build the records inside one per-plugin `try`, and drop the five
  checks.
- Step: 1.
- Outcome: removed in 75183dc; one `try` per plugin, and since c982a8d a bad
  record skips the whole plugin.

### 10. The shot queue's Add button and file dialog

- Where: `shotqueue.py:ShotQueueWidget`: its arguments and attributes (171,
  176, 182, 184), the button and its row (209-215, 220), its connection
  (222-223), `add_files` (298-304) and `prompt_for_files` (306-315).
- Core lines: 30.
- What it does: an "Add" button under the list opens a file dialog at the last
  folder used, and adds the shots chosen.
- Not upstream: 276eba7 (2026-03-17); `connect_add_button` in c515061
  (2026-04-06). Upstream BLACS had an "Add shots" button.
- Request: none found beyond the plan's "add". Searched for
  `file_dialog_filter`, `last_opened_shots_folder` and `prompt_for_files`.
- Callers: runmanager passes `connect_add_button=False` and hides the button
  (`queueing.py:163, 171`). `add_files` and `prompt_for_files` never ran in the
  trace.
- Removal user-visible: no; the button is already hidden.
- Proposed: remove. runmanager drops `file_dialog_filter=`,
  `connect_add_button=False` and the `hide()` call.
- Step: 1, possibly 4.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 11. A second type check on app configs, which drops None

- Where: `labscript_utils/labconfig.py:_to_toml_compatible` (250-274), and the
  `None` filter in `save_appconfig` (299, docstring 290-293).
- Core lines: 30.
- What it does: before `tomli_w` writes an app config, it turns tuples into
  lists. It raises with a `section/option[index]` location for a value TOML
  cannot hold. It leaves out any `None`, at any depth in a dict.
- Not upstream: dee0033 (2026-03-19); the `None` dropping came in 8a1687b
  (2026-08-28), and was extended to nested dicts in ad53b5b (2026-10-07).
- Request: partly found. Item 9 of the meta repo's review triage (74213d7)
  asks that a nested `None` be treated "the same way" as one at section level;
  ad53b5b did that. The section-level dropping came from an agent audit, whose own
  message says no payload produces a `None`. Nothing found asks for the type
  check: `tomli_w` already writes tuples and raises for `None`, sets and
  non-string keys.
- Callers: every app's saved payload was read (runmanager, its queue, lyse and
  runviewer), and none can hold a `None`. lyse's routine-box payload was not read
  line by line.
- Removal user-visible: no for any current payload. A future `None` would raise
  `tomli_w`'s own `TypeError`.
- Proposed: remove the checker. Ian chooses whether `None` is dropped, which
  would keep one filter line, or raises, the same way at every level.
- Step: 1, possibly 3.
- Outcome: removed in 5b37296. Ian: a `None` raises tomli_w's own error at every
  level. `dump_toml_file` now serialises before it opens the file, so a failed
  save leaves the old config intact. Since 89ce0b5 the INI conversion leaves
  out an option upstream wrote as `None`, so such a file still converts
  unaided.

### 12. BasePlugin's default setup activity

- Where: `plugins.py:BasePlugin.plugin_setup_complete` (806-817),
  `BasePlugin.get_setup_activities` (819-834), and one sentence of the module
  docstring (588-590).
- Core lines: 29.
- What it does: makes a `BasePlugin` subclass that overrides only
  `plugin_setup_complete` run it as one setup activity.
- Not upstream: 465943d (2026-04-24) and 57c889f (2026-05-11).
- Request: none found. Searched for `get_setup_activities` and
  `setup activities`.
- Callers: `HydePlugin` overrides `get_setup_activities` without calling
  `super()`, and hyde defines no `plugin_setup_complete`. blacs plugins do not
  inherit `BasePlugin`. For any plugin without the method,
  `PluginManager.setup_complete` (1444-1451) already builds the same activity.
- Removal user-visible: no.
- Proposed: remove both defaults and the sentence; the manager's branch is the
  one implementation.
- Step: 1, possibly 2.
- Outcome: removed in 2023a8a.

### 13. Checks on what a contribution hook returns

- Where: `plugins.py:PluginManager._get_contributions` (1291-1302).
- Core lines: 11.
- What it does: when `get_ui_contributions` or `get_menu_contributions`
  returns `None`, a dict, a string or a non-iterable, it is logged and treated as
  contributing nothing.
- Not upstream: 3cef7b3 (2026-04-25).
- Request: none found before the code; PRD story 12.
- Callers: hyde's 11 contribution hooks all return lists of dicts; blacs
  defines none.
- Removal user-visible: no. Checked in a scratch copy: each bad shape is still
  logged and skipped.
- Proposed: simplify to `return list(hook() or ())` inside the existing `try`.
- Step: 1.
- Outcome: removed in 2cce0b5, with entry 14.

### 14. Contributions read into a list before they are tested

- Where: `plugins.py:PluginManager._get_contributions` (1304-1314).
- Core lines: 11.
- What it does: reads a plugin's contributions into a list inside its own
  `try`. This stops a generator that yields nothing from counting as a
  contribution when entry 7's `menus` check runs.
- Not upstream: 6b7a9d0 "Materialise plugin contributions before testing them"
  (2026-08-28), a fix for an audit finding.
- Request: none found; the message names an audit defect, not a need.
- Callers: no plugin returns a generator.
- Removal user-visible: no.
- Proposed: remove with entry 7; entry 13's `list(...)` stays inside the `try`.
- Step: 1, possibly 3: a bug-fix guard whose cause is entry 7.
- Outcome: removed in 2cce0b5, with entry 13.

### 15. Collecting services: inputs that are not mappings

- Where: `plugins.py:PluginManager.collect_services` (1385-1393, 1408-1415).
- Core lines: 17.
- What it does: logs and replaces with an empty registry an application
  registry that is not a mapping. It skips a plugin whose `get_services()`
  returns `None` or a non-mapping.
- Not upstream: aaa642b "Added ability to share services." (2026-04-27).
- Request: none found. Searched aaa642b, and the meta repo for
  `collect_services` and `services`.
- Callers: one, hyde (`main/__init__.py:360`), which passes a dict. All 11 hyde
  `get_services` return dict literals.
- Removal user-visible: no. A bad plugin is still caught by the existing
  `try`.
- Proposed: `services = dict(base_services or {})`, and
  `services.update(plugin.get_services())` inside the `try`.
- Step: 1.
- Outcome: removed in 1010e61.

### 16. A home-directory `~` in the window title

- Where: `labscript_utils/labconfig.py:format_path_for_display` (36-50).
- Core lines: 15.
- What it does: shows the config path in the title bar with the home directory
  written `~`, or `%USERPROFILE%` on Windows.
- Not upstream: f1d4a98 "Show active config path in window title"
  (2026-04-07).
- Request: the title bar showing the path was asked for (branch
  `UpdatedTitleBars`). Nothing found asks for the abbreviation; f1d4a98 has no
  body.
- Callers: every app's title goes through it. `USERPROFILE` appears only
  here, so no test depends on it.
- Removal user-visible: yes; the title shows the absolute path.
- Proposed: simplify to `os.path.abspath(filename)` in
  `set_config_window_title`.
- Step: 1. Lower confidence: it is a detail of a requested feature.
- Outcome: kept, and extended in edd75a2. Qt passes a title to the window
  unchanged, and the macOS 26 title bar cuts the end with "…", losing the file
  name. Ian: a displayed path longer than `max_length`, 60 characters by
  default, now loses its middle instead, keeping the drive or install at the
  start and the folder and file at the end. No resize tracking.

### 17. Shot-queue change and selection signals

- Where: `shotqueue.py`: the `queueChanged` and `selectionChanged` signals
  (163-164), their connections (228-231), `selected_files` (241-242),
  `_on_queue_changed` (458-460) and `_on_selection_changed` (462-464).
- Core lines: 14.
- What it does: announces each change to the rows, and each new selection by
  path.
- Not upstream: 276eba7 (2026-03-17).
- Request: none found; searched for `queueChanged` and `selectionChanged`.
- Callers: none connect either. runmanager's `queueChanged` belongs to its own
  `QueueManager` (`queueing.py:1025`). The handlers run on every change and
  compute paths that no one receives.
- Removal user-visible: no.
- Proposed: remove.
- Step: 1, possibly 4.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 18. Package-level names in labscript_utils.qtwidgets

- Where: `labscript_utils/qtwidgets/__init__.py` (14-33).
- Core lines: 14.
- What it does: lets `labscript_utils.qtwidgets.ShotQueueWidget` resolve on
  first use, without importing Qt for every submodule.
- Not upstream: `master`'s file is the licence banner alone. The names came in
  276eba7, and were made lazy in cbbcc4f (2026-03-17).
- Request: none found; searched for `lazily` and `qtwidgets`.
- Callers: none. Every repo imports `labscript_utils.qtwidgets.<module>`
  (control: labscript-utils' own `qtwidgets.analoginput` import matches).
- Removal user-visible: no.
- Proposed: restore `master`'s banner-only file.
- Step: 1.
- Outcome: removed in ef1d5c3; the file is `master`'s again.

### 19. The shot queue's own "Delete selected rows" menu

- Where: `shotqueue.py:ShotQueueTreeView.contextMenuEvent` (107-116).
- Core lines: 10.
- What it does: a right-click on the list offers "Delete selected rows".
- Not upstream: 7c13f18 "Use context-menu deletion in shot queue widget"
  (2026-04-06).
- Request: none found; searched for `contextMenu` and `Delete selected`.
- Callers: runmanager sets a custom context-menu policy and shows its own menu
  (`queueing.py:174-177`). Checked in a scratch copy: under that policy the event
  never reaches this method.
- Removal user-visible: no.
- Proposed: remove.
- Step: 1.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 20. When two plugins offer the same service name, the first keeps it

- Where: `plugins.py:PluginManager.collect_services` (1417-1425).
- Core lines: 9.
- What it does: a plugin offering a service name that is already registered
  does not replace it, and an error is logged. "First" follows `os.listdir`
  order.
- Not upstream: aaa642b (2026-04-27).
- Request: none found; searched as for entry 15.
- Callers: no collision exists. hyde's 11 plugin service names are distinct
  from each other and from its 32 application keys; a check that can fail
  confirmed this.
- Removal user-visible: no today. If a collision were introduced, the later
  plugin would win silently.
- Proposed: remove, so the later registration wins. If Ian wants a collision to
  stay loud, raise `ValueError` at it instead.
- Step: 1.
- Outcome: changed in cf70352. Ian: a duplicate service name raises
  `ValueError`, naming the service and the plugin.

### 21. Saving and restoring the shot queue's file list

- Where: `shotqueue.py:ShotQueueWidget.get_save_data` (332-336) and
  `restore_save_data` (338-340).
- Core lines: 8.
- What it does: returns and restores the queued files and the last folder
  opened.
- Not upstream: 276eba7 (2026-03-17).
- Request: none found beyond the plan's "queue serialization".
- Callers: none. runmanager saves its queue through
  `queue_controller.export_state()`, and refers to its queue widget at only
  four sites (`__main__.py`), none of them these methods.
- Removal user-visible: no.
- Proposed: remove.
- Step: 1, possibly 4.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 22. Rows and columns given as bare strings

- Where: `shotqueue.py`: `_create_row_from_info` (359-360) and
  `_create_display_item_from_info` (422, 426-429).
- Core lines: 7.
- What it does: accepts a row given as a plain path, or a column as plain text,
  instead of the dict form.
- Not upstream: 5876c9b "Move shot queue column support into shared widget"
  (2026-04-06).
- Request: none found; searched for `set_row_infos`.
- Callers: runmanager builds only dict rows and columns. Its `set_queue_paths`
  passes a non-dict through (`queueing.py:248-252`), but nothing supplies one.
- Removal user-visible: no.
- Proposed: remove, together with runmanager's pass-through.
- Step: 1, possibly 4.
- Outcome: removed in b857f3e, with the shot-queue group; runmanager's matching
  edits are with its owner.

### 23. The `preserve_unresolved` switch on output-path templates

- Where: `labscript_utils/lookup_format.py`: `format_lookup_string` and
  `_LookupFormatter` (50, 59, 71, 81, 85, 90, 116).
- Core lines: 7.
- What it does: leaves every unresolved field in a template in place, whatever
  its name.
- Not upstream: 65f8ccd "Add lookup formatter for runmanager templates"
  (2026-04-07).
- Request: none found; searched for `preserve_unresolved`. CODEX.md asks for
  the opposite: preserve only `globals[...]`, without swallowing typos in other
  names. `preserve_unresolved_roots` does exactly that.
- Callers: none. runmanager passes only `preserve_unresolved_roots=('globals',)`
  (`__init__.py:644, 653`).
- Removal user-visible: no.
- Proposed: keep only `preserve_unresolved_roots`.
- Step: 1.
- Outcome: removed in bb1570e.

### 24. Starting the next indexed file name from an existing suffix

- Where: `labscript_utils/file_utils.py:next_available_indexed_filepath`
  (23-25, 36-39).
- Core lines: 7.
- What it does: with `start=None`, the search starts one past the index already
  on the path.
- Not upstream: the module is new (454570c, 2026-03-26); the `None` default came
  in 8bf4faa "Make indexed filepath start explicit" (2026-04-06).
- Request: none found.
- Callers: all four call sites pass `start=` (blacs `shot_execution.py:399`;
  runmanager `__main__.py:2804, 2810, 4993`).
- Removal user-visible: no.
- Proposed: make `start` required.
- Step: 1, possibly 4.
- Outcome: kept. runmanager's `reindex_run_file_infos` passes `start=None` when
  a batch joins the last sequence and no sequence is recorded; making `start`
  required failed 8 runmanager tests.

### 25. Checking that a plugin's event handlers are a mapping

- Where: `plugins.py:PluginManager._get_plugin_event_handlers` (1595-1600).
- Core lines: 6.
- What it does: logs a plugin whose event hook returns something other than a
  mapping, and treats it as having no handlers.
- Not upstream: dd8664f (2026-04-26).
- Request: none found before the code; PRD story 12.
- Callers: every blacs and hyde hook returns a dict or `None`.
- Removal user-visible: no. Checked in a scratch copy: such a plugin is still
  caught and logged by the `except` in `get_event_handlers`, and the good
  plugin's handlers are returned.
- Proposed: remove.
- Step: 1.
- Outcome: removed in 025bdcf.

### 26. MenuBuilder without an icon factory

- Where: `plugins.py:MenuBuilder` (875-877, 897-899).
- Core lines: 6.
- What it does: without an `icon_factory`, a menu item's `icon` is silently
  ignored.
- Not upstream: 465943d (2026-04-24); upstream blacs's `create_menu` always
  used `QIcon`.
- Request: none found; searched for `icon_factory`.
- Callers: blacs, the only caller, passes `QIcon` (`__main__.py:346`). Only a
  labscript-utils test builds one without it.
- Removal user-visible: no.
- Proposed: make `icon_factory` required, and use it whenever `icon` is given.
- Step: 1.
- Outcome: changed in 7116dad; the factory is required.

### 27. An option to keep labconfig section names' case

- Where: `labscript_profile/toml_config.py:TomlConfigParser.__init__` (52-54,
  57-58) and `_canonical_section_name` (63-64).
- Core lines: 6.
- What it does: `lowercase_keys_and_sections=False` turns off lower-casing of
  section and key names.
- Not upstream: 806fab5 (2026-03-19).
- Request: none found; searched for `lowercase_keys_and_sections`. CODEX.md
  records the lower-case policy, not a switch for it.
- Callers: none pass it; both constructions use the default.
- Removal user-visible: no.
- Proposed: remove; lower-casing stays.
- Step: 1, possibly 4.
- Outcome: removed in dfda81c.

### 28. LinkIndicator's `interval` and `status_width` arguments

- Where: `labscript_utils/qtwidgets/link_indicator.py:LinkIndicator.__init__`
  (52-53, 58-59, 75, 77).
- Core lines: 6.
- What it does: lets a caller change the seconds between probes (2) and the
  fixed width (220 px).
- Not upstream: 06fb72a (2026-10-04) and 500cb90 "Give the link indicator a
  fixed width, set in pixels" (2026-10-04).
- Request: the fixed width was Ian's, and he accepted 220 px. Nothing found asks
  that it be an argument. The server-interfaces spec and CODEX.md list both
  arguments, but were written after the code.
- Callers: none of the six constructions passes either. Only labscript-utils'
  own test passes `interval`.
- Removal user-visible: no.
- Proposed: fix 220 px, and let the test assign `indicator.interval`. The
  weakest entry; Ian may count it settled by his width decision.
- Step: 1.
- Outcome: changed in a17a9b5. Ian: `status_width` stays; `interval` is an
  attribute the test assigns.

### 29. MenuContext's icon factory

- Where: `plugins.py:MenuContext.__init__` (923, 927-928, 932) and the example
  key `'icon'` (214).
- Core lines: 4.
- What it does: shows a menu contribution's `icon` through an
  application-supplied factory.
- Not upstream: 3cef7b3 (2026-04-25).
- Request: none found; CODEX.md lists "icons" among the features, describing
  the code.
- Callers: hyde builds `HydeMenuContext` without a factory, and no contribution
  has an `icon`.
- Removal user-visible: no.
- Proposed: remove. hyde's `HydeMenuContext` would also lose its `icon_factory`
  argument and its icon branch (3 to 5 lines).
- Step: 1, possibly 4, with the base `render`.
- Outcome: removed in 58c931e; hyde's matching edit is with its owner.

### 30. A guard for application classes missing their names

- Where: `labscript_utils/labconfig.py:LabscriptApplication.get_default_config_file`
  (83-86).
- Core lines: 4.
- What it does: raises `NotImplementedError` when a subclass sets no `app_name`
  or `default_config_filename`.
- Not upstream: f1d4a98 (2026-04-07).
- Request: none found. The deleted labscript-utils audit (finding L11) defends
  it, and is an agent's own justification.
- Callers: runmanager, lyse and runviewer set both names. BLACS sets neither,
  and never calls the method.
- Removal user-visible: no.
- Proposed: remove.
- Step: 1, possibly 4.
- Outcome: removed in a02dfc1.

### 31. List options given as a tuple or a bare value

- Where: `labscript_profile/toml_config.py:as_config_list` (24, 26, and a
  docstring sentence).
- Core lines: 3.
- What it does: besides a comma-separated string or a TOML array, accepts a
  tuple, and turns any other value into a one-item list.
- Not upstream: 679bb78 "Accept TOML arrays for list-valued labconfig options"
  (2026-08-28), from an agent audit.
- Request: none found; searched for `as_config_list`.
- Callers: two, both in labscript-utils, both reading the labconfig. TOML never
  produces a tuple.
- Removal user-visible: no.
- Proposed: accept a string or a list only. The array form itself came from a
  bug fix (step 3).
- Step: 1.
- Outcome: changed in e39ce15; a string is split, and anything else is iterated.

### 32. get_qapplication's `argv` argument

- Where: `labscript_utils/splash.py:get_qapplication` (61, 65).
- Core lines: 2.
- What it does: lets a caller choose the QApplication's argument list.
- Not upstream: 5ccbfba "Configure shared Qt application defaults"
  (2026-03-18).
- Request: none found; CODEX.md's `MacOS_icon` entry asks for
  `application_name`, not `argv`.
- Callers: blacs and lyse call it with no arguments, and `Splash` passes only
  `application_name` and `icon_path`.
- Removal user-visible: no.
- Proposed: `argv = sys.argv`.
- Step: 1.
- Outcome: removed in 6410d75.

### 33. Two checks in configure_qapplication that cannot fail

- Where: `splash.py:configure_qapplication` (43, 53).
- Core lines: 2.
- What it does: skips the macOS icon when it reads as null, and skips Fusion
  when Qt cannot make it.
- Not upstream: 5ccbfba (2026-03-18) and 5725e3e (2026-03-26).
- Request: none found; CODEX.md's `MacOS_icon` entry asks only that the icon be
  applied and the Fusion style kept.
- Callers: in a scratch copy under PyQt6, Fusion is always available (control:
  a made-up style name returns `None`), and a null icon raises nothing. Splash
  raises on an unreadable icon anyway.
- Removal user-visible: no.
- Proposed: remove both checks.
- Step: 1.
- Outcome: removed in 3558785.

### 34. Name order among one plugin's equal-priority setup activities

- Where: `plugins.py:PluginManager.setup_complete` (1507, `activity['name']` in
  the sort key).
- Core lines: 1.
- What it does: runs one plugin's equal-priority activities in name order
  rather than the order it returned them.
- Not upstream: 57c889f (2026-05-11).
- Request: none found; searched as for entry 9.
- Callers: the activities of each hyde plugin have distinct priorities, and a
  blacs plugin has one activity. The plugin-name tie-break, which hyde does use,
  stays.
- Removal user-visible: no.
- Proposed: sort by `(priority, module_name)`.
- Step: 1.
- Outcome: removed in 6980591.

### 35. Index and type errors in a template reported as unresolved

- Where: `lookup_format.py:_LookupFormatter._resolve_field` (132).
- Core lines: 1.
- What it does: reports `{globals[l][5]}` past the end of a list as an
  unresolved field named "globals", in place of Python's own error.
- Not upstream: d0175eb "Tighten lookup format unresolved handling"
  (2026-04-07); 65f8ccd caught `KeyError` only.
- Request: none found; searched for `IndexError`, `missing global` and
  `unresolved`.
- Callers: nothing catches `UnresolvedLookupField` by name. The preserving
  pass runs with no globals, so it never reaches an index.
- Removal user-visible: only the error a malformed index gives, which would
  then name the real fault.
- Proposed: catch `KeyError` only. Low confidence; the line fits the
  "unresolved" idea.
- Step: 1, possibly 3.
- Outcome: changed in fe68382.

### Total

35 candidates hold 743 core lines. `labscript_utils` and `labscript_profile`
hold 9750 non-blank lines on `CodeHealth` and 6917 on `master`, so the
candidates are about a quarter of what the fork adds there. The largest groups
are the INI paths (entries 1, 3 and 8: 197 lines), the shot queue features
runmanager turns off (entries 2, 4, 10, 17, 19, 21 and 22: 206 lines), and the
plugin framework's guards, warnings and defaults (243 lines).

Removal changes what a user sees in four entries: 1 and 3 for anyone still
holding INI files, 8 only for a script of their own that opens one, and 16 in
the title bar. Entry 5 changes only the log.

### Outcome

Ian kept entries 1, 3, 8 and 16; entry 24 was kept because a runmanager path
passes `start=None`. Entries 11, 20 and 28 were done as Ian decided, and the
rest as proposed, in 23 commits from b857f3e to 3558785, followed by three from
the code-quality review (23571b2, c982a8d, 2bb4f6d). `labscript_utils` and
`labscript_profile` went from 9744 to 9216 non-blank lines, 528 fewer.
runmanager and hyde each need a small matching edit, which their owners make.

### Seen for later steps

- Step 2, duplication:
  - The non-dict menu-contribution check is written three times:
    `setup_contexts`, `MenuContext.render` and hyde's `HydeMenuContext.render`.
  - `ShotQueueWidget.selected_ids` and `select_ids` are near-identical loops.
  - `_resolve_appconfig_save_path` is a one-line forward. After entry 3,
    `_resolve_appconfig_load_path` is the same call.
  - `AA_DontShowIconsInMenus` is set in `configure_qapplication` and again in
    runmanager.
- Step 3, guards from bug fixes:
  - The non-boolean plugin enable flag in `PluginManager.discover_modules`
    (1158-1173), from 35b76df and 16c2e0b.
  - `PluginManager._setup_action_args` (4cf6f52).
  - `ZMQServer.handler`'s reply checks, whose cause is in zprocess.
  - The array form of `as_config_list` (679bb78).
  - The `default` table in `load_appconfig` (a54da76).
- Step 4, dead code and compatibility leftovers:
  - The base `MenuContext.render` (950-1088), already decided.
  - `BasePlugin.get_callbacks`, `PluginManager.get_callbacks` with its
    `warnings` import, and `BasePlugin.get_menu_class`, which the meta repo's
    `issues/seen_while_mapping.md` lists as compatibility leftovers.
  - The no-argument `plugin_setup_complete()` fallback, which no plugin uses.
  - The three dead-code entries in `issues/seen_while_mapping.md`
    (`connections`, `headerview_with_widgets`, `toolpalette`).
  - `ShotQueueWidget._update_button_states`, a `pass` stub, and
    `FILEPATH_COLUMN`, which nothing uses.
  - `TomlConfigParser.to_toml_dict` and `write_toml`, which nothing calls.
  - `COMMUNICATION_DEFAULT_TIMEOUT`, which was made public but is imported
    nowhere.
- Step 5, documents: the `plugins.py` module docstring is 481 lines, longer
  than the code it documents. It still tells authors to call the deprecated
  `PluginManager.get_callbacks()`.
- Step 6, style: `lookup_format.py` and `plugins.py`, both created by the fork,
  carry a Monash University banner; whether rule 14 applies is a step-6
  question.

## Step 2: duplication

"The map shows where a problem is solved twice. One implementation stays." For
the pilot that means two kinds:

- a problem solved twice inside labscript-utils;
- a problem solved in several repos whose one implementation belongs in
  labscript-utils, consolidated across the suite in one round.

Each entry gives:
- every copy, with its repo, file and function;
- how the copies differ, read from the code;
- the one implementation that stays;
- the core lines saved;
- the edits each other repo makes. Those edits go to each repo's owner in the
  same round as the labscript-utils change, and only once Ian has approved.

Refs and counting:
- Refs are `Development`, except labscript-utils `CodeHealth` at 6df3017,
  runmanager `CodeHealth` (the same as Development outside `queueing.py`) and
  hyde `HEAD`.
- "Upstream" means the copy is on that repo's `master`.
- Core lines are non-blank lines, docstrings and comments included. Where a
  survivor was drafted in a scratch copy, the figure is that draft's.
- A new module adds the suite's 12-to-13-line licence banner, which the figures
  do not include unless stated.

Candidates came from four sources:
- this file's step 2 notes;
- the meta repo's `issues/seen_while_mapping.md`;
- the librarian's list, from labscript-library edfa619;
- three sweeps: inside labscript-utils, non-GUI helpers across repos, and GUI
  code across repos. The sweeps used name scans and clone scans of every
  repository.

Every "no other caller" claim was searched with `git -C <repo> grep` over every
file of every repo, beside a control that matches. hyde is left out as a source
of duplicates (Ian), but counted as a consumer.

### 1. `__version__.py`, copied into eight repos

- Copies: `__version__.py` in labscript, labscript-devices, labscript-utils,
  runmanager, blacs, lyse, runviewer and labscript-suite.
  - All are upstream, 25 lines each, and byte-identical apart from runmanager's
    missing final newline.
  - zprocess (13 lines) and desktop-app (22) have their own variants. They
    cannot join, because labscript-utils depends on zprocess, not the other way
    round.
- Differences: none among the eight. Each does the same thing:
  - in a git checkout, `setuptools_scm` with `release-branch-semver` and
    `node-and-date`;
  - otherwise `importlib.metadata`;
  - else `None`.
- Stays: one function in `labscript_utils/versions.py`, called from each
  `__init__` as `__version__ = package_version(__package__)`.
  - The existing `versions.get_version` is not a drop-in. It uses no version
    scheme: in a scratch git repo it gave `1.0.1.dev1` where these files give
    `1.1.0.dev1`.
  - It also returns sentinel classes where these files return `None`.
- Core lines saved: 171.
  - Seven repos each delete 25 lines and add 1.
  - labscript-utils' own 25 lines become about 21, plus 1 import.
- Consumer edits: delete `__version__.py`, and change one `__init__` line, in:
  - labscript `labscript/__init__.py:14`;
  - labscript-devices `labscript_devices/__init__.py:5`;
  - runmanager `runmanager/__init__.py:41`;
  - blacs `blacs/__init__.py:14`;
  - lyse `lyse/__init__.py:31`;
  - runviewer `runviewer/__init__.py:15`;
  - labscript-suite `labscript_suite/__init__.py:1`.
  Nothing else imports the module.
- Visible to a user: no. `pkg.__version__` keeps its value.
- Decision for Ian: this is upstream boilerplate in seven repos, so it widens the
  fork's difference from upstream at every sync. The new function was not run in
  a real checkout.

### 2. Output widgets: lock menu, wheel pass-through, lock and unlock, four times

- Copies, all upstream, in `labscript_utils/qtwidgets/`:
  - `analogoutput.py:AnalogOutput`: eventFilter 224-232, `_menu_triggered`,
    lock 241-246, unlock 248-253;
  - `digitaloutput.py:DigitalOutput`: eventFilter 43-64, `_menu_triggered`,
    lock 73-77, unlock 79-83;
  - `enumoutput.py:EnumOutput`: eventFilter 125-146, `_menu_triggered`,
    lock 155-160, unlock 162-167;
  - `imageoutput.py:ImageOutput`: eventFilter 169-191, `_menu_triggered`,
    lock 200-205, unlock 207-212;
  - the image widget's children pop the same menu twice more.
  - The disabled-widget wheel pass-through is 12 lines, written three times.
- Differences:
  - `ImageOutput.eventFilter` returns True after its menu; the other three fall
    through. The survivor falls through.
  - The menu label is read from a different child in each widget. The survivor
    reads one `_lock_target`.
  - The lock keywords differ: `notify_ao`, `notify_do`, `notify_eo` and
    `notify_Image`. They become one, `notify_output`.
  - An offscreen drive of the old and drafted widgets agreed, except for the
    image's return value. Nothing in the suite handles that event above the
    widget.
- Stays: a `LockableOutput` mixin in a new `qtwidgets/lockable.py`. Each widget
  becomes `class X(LockableOutput, <its Qt base>)`.
  - `set_AO`, `set_DO`, `set_EO` and `set_Image` stay per class, because they
    call `remove_widget` with different arguments.
  - `LockableOutput` is a new public name, for the librarian.
- Core lines saved: 91, with the new file's banner counted. 14 of these are
  step 4 matter that goes with the edit: EnumOutput's unused `_lock_action`, and
  a commented-out `ImageView.eventFilter`.
- Consumer edits: none. blacs `output_classes.py` calls `lock(False)` and
  `unlock(False)` positionally, and the theme plugin styles by class name; both
  keep working. The stylesheet pixels matched offscreen.
- Visible to a user: no. A lab-local BLACS tab calling
  `widget.lock(notify_do=False)` by keyword would break; nothing in the suite
  does.

### 3. Starting a zprocess server, and connecting to zlock and zlog

- Copies, all upstream:
  - the `main()` of `remote.py` (30-57), `zlock.py` (28-60) and `zlog.py`
    (29-60): the same command build, the same security block, and the same
    daemon-or-foreground launch;
  - `ls_zprocess.connect_to_zlock_server` (421-452) and
    `ensure_connected_to_zlog` (458-483): the same ping, else start the daemon
    and ping again.
- Differences: the module name and the port key. Each also has its own extras:
  - zlog adds its rotating-file arguments;
  - remote adds `-tui`;
  - zlock refuses a remote `zlock_host`, checks the protocol version and sets
    the default timeout;
  - zlog's connect returns early once connected.
  Drafted and compared: the command lines matched for 3 modules, 3 security
  settings and 3 argument lists, and the ping and daemon sequences matched.
- Stays:
  - `run_server(module, port, *extra_args, tui=False)` and a private
    `_ping_starting_locally` in `ls_zprocess.py`;
  - the three `-m` scripts, as the documented entry points, each reduced to its
    own configuration plus one call;
  - `connect_to_zlock_server` and `ensure_connected_to_zlog`, which keep their
    names and their extras.
- Core lines saved: 68.
- Consumer edits: none. Callers of the two connect functions, and the `-m`
  command lines, are unchanged.
- Visible to a user: no. `run_server` is a new public name.

### 4. Save, save as, revert and load configuration in lyse and runmanager

- Copies, all upstream: lyse `__main__.py:Lyse` and runmanager
  `__main__.py:RunManager` each have:
  - `on_save_configuration_triggered`;
  - `on_revert_configuration_triggered`;
  - `on_save_configuration_as_triggered`;
  - `save_configuration`;
  - `on_load_configuration_triggered`.
  That is 72 lines in lyse (255-368) and 74 in runmanager (4272-4413).
  runviewer's `save_configuration` (384-390, not upstream) is a seventh copy of
  the save body.
- Differences:
  - the state key, which is `<app_name>_state` in each;
  - the dialog captions, which differ by app name;
  - the error-dialog helper;
  - three lines in runmanager's Save as, which put the path on the Save menu
    item.
  The survivor keeps runmanager's, so lyse's Save item would start showing the
  path after a Save as.
- Stays: a `LabscriptGuiApplication(LabscriptApplication)` in a new
  `qtwidgets/application.py`, which holds the five methods and reads its key and
  captions from `app_name`.
  - It cannot go on `LabscriptApplication` itself: `labconfig.py` is imported by
    the compiler (`labscript/compiler.py:19`) and must stay free of Qt.
  - Each app keeps its own `get_save_data()` and `load_configuration()`.
- Core lines saved: 67.
- Consumer edits:
  - lyse `__main__.py`: imports 50-55, class line 113, and delete 255-294 and
    330-368;
  - runmanager `__main__.py`: imports 65-70, class line 2064, and delete
    4272-4314 and 4376-4413;
  - runviewer `__main__.py`: imports 71-77, class line 205, and delete 384-390.
  - The menu wiring, the `.ui` actions and runmanager's
    `tests/test_configuration.py` are unchanged.
- Visible to a user: yes, in two small ways.
  - lyse's Save item follows a Save as, which it does not do today.
  - lyse's Load prompt says "which groups are active/open", wording copied from
    runmanager; lyse has no groups.
- Decision for Ian: whether labscript-utils should hold a GUI application layer
  at all. Entries 12 and 19 share the same new module.
- Optional, about 17 more lines: the "save changes?" Yes/No/Cancel prompt
  appears four times (lyse 232, 340; runmanager 2512, 4385). One method could
  serve all four, but the wording differs per app.

### 5. Views that signal a left click, in lyse and runmanager

- Copies, both upstream:
  - lyse `widgets.py:TableView` 95-141 and `TreeView` 143-187, each with its own
    mouse handlers. The docstring claims a shared mixin is impossible;
    runmanager's shows it works.
  - runmanager `__main__.py:ItemView` 514-601, a mixin under `TreeView` and
    `TableView`.
- Differences: runmanager reads the pressed index before the base handler runs,
  and lyse after; they also call different event APIs for the same point.
  runmanager adds key handling, highlighting and cursor moves, which it keeps.
  Simulated mouse sequences gave identical signals from both.
- Stays: a `LeftClickMixin`, plus `TreeView` and `TableView` built on it, in a
  new `qtwidgets/leftclick.py`. It takes runmanager's press order.
  runmanager's `ItemView` derives from it and keeps its extras.
- Core lines saved: 67.
- Consumer edits:
  - lyse: delete `widgets.py:95-187`; `filebox.py:690` and `routines.py:63`
    register the new classes.
  - runmanager: `__main__.py:514-564` reduced to the extras, plus an import.
  - The `.ui` files promote by class name and need no edit.
- Visible to a user: no. `lyse.widgets.TreeView` and `TableView` go, but nothing
  outside lyse uses them.

### 6. File dialogs that return a path

- Copies: the same steps at 22 call sites: call `QFileDialog`, unwrap the tuple,
  return on cancel, then `os.path.abspath`.
  - runmanager: 8 sites;
  - lyse: 7, in `__main__.py`, `filebox.py` and `routines.py`;
  - runviewer: 5;
  - blacs: `shot_execution.py:223`;
  - labscript-utils: `qtwidgets/imageoutput.py:38`.
  17 of the 22 are upstream.
- Differences: none in behaviour. Two sites never apply `abspath` today and
  would gain it.
- Stays: `open_file`, `open_files`, `save_file` and `choose_folder` in a new
  `qtwidgets/file_dialogs.py`. Each returns an absolute path, or None on cancel.
- Core lines saved: 55. The smaller alternative is step 4 only: the
  `if type(x) is tuple` test is always true under PyQt6, so deleting it saves
  one line at each of about 25 sites with no new module.
- Consumer edits: the 22 sites, and one import each in runmanager `__main__.py`,
  lyse `__main__.py`, `filebox.py` and `routines.py`, runviewer `__main__.py`,
  and blacs `shot_execution.py`.
- Visible to a user: no.

### 7. `unitconversions.test`, a copy of `example1`

- Copies, both upstream: `unitconversions/test.py:test` and
  `unitconversions/example.py:example1`.
- Differences: `base_unit` (`MHz` against `V`), and where `derived_units` is
  set. The conversions themselves are identical, character for character.
- Stays: `example1`, which labscript's example uses.
- Core lines saved: 46, the whole file with its banner.
- Consumer edits: none. No repo names `test`.
- Visible to a user: possibly. Every unit-conversion class reaches a sequence's
  namespace through `from labscript import *`. A lab sequence or an old shot
  file naming `unitconversions.test.test` would break; nothing in the suite
  does. Ian's call. This is also a step 4 candidate.

### 8. Finger tabs, in labscript-utils and runmanager

- Copies, both upstream:
  - labscript-utils `qtwidgets/fingertab.py`, the gist: fixed 100x25 tabs, text
    only. Only the Preferences dialog uses it (`settings.py:16, 90`).
  - runmanager `__main__.py:FingerTabBarWidget`, `TabToolButton` and
    `FingerTabWidget` (296-496): the same gist grown, with sizes from the text,
    icons, movable and closable tabs, and clipping.
- Differences: runmanager's tabs measure 180x30 or more. The Preferences dialog
  would show the larger tabs.
- Stays: runmanager's three classes, moved into `qtwidgets/fingertab.py` in
  place of the gist.
- Core lines saved: 29, plus 12 if the file's `__main__` demo goes, which it
  must change anyway.
- Consumer edits:
  - runmanager: delete `__main__.py:296-496` and import the classes. Its tests,
    which take `FingerTabWidget` from `runmanager.__main__`, still find it.
  - `main.ui` needs no edit.
- Visible to a user: yes, larger tabs in the Preferences dialog. Also,
  `FingerTabBarWidget(width=, height=)` becomes `minwidth=, minheight=`; only the
  demo passes them.

### 9. Restyling on a theme change, and the first-paint signal

- Copies:
  - The child restyle on a palette or style change is written in three apps:
    lyse `utils/gui.py:ThemedWindow` (a mixin), blacs
    `__main__.py:BLACSWindow.changeEvent`, and runmanager
    `RunmanagerMainWindow.changeEvent` with `on_theme_changed`.
  - The first-paint signal is written twice: lyse `LyseMainWindow` and
    runmanager `RunmanagerMainWindow`.
  Upstream had the loop inline in each; the mixin and the signal are the fork's.
- Differences: the order of `setStyleSheet` and `setPalette`, which cannot be
  seen. Each app's own follow-up work, such as blacs's tab colours and
  runmanager's group colours, stays with the app.
- Stays: lyse's `ThemedWindow` with a `themeChanged` signal, and a first-paint
  mixin beside it, in a new `qtwidgets/themed_window.py`. Checked offscreen
  against what blacs's theme test pins.
- Core lines saved: 25.
- Consumer edits:
  - lyse: the base classes at `__main__.py:81`, `analysis_subprocess.py:83` and
    `routine.py:55`; delete `utils/gui.py:128-141` and `LyseMainWindow`'s
    first-paint code.
  - blacs: the base class at `__main__.py:122`, delete 148-167, add a slot
    connected to `themeChanged`; `tests/test_theme_events.py` follows the slot.
  - runmanager: the base class at `__main__.py:2024`, and delete 2025-2029,
    2031-2033, 2035-2042, 2050-2055 and 2501-2505.
- Visible to a user: no.

### 10. `dict_diff`, in labscript-utils and runmanager (approved)

- Copies, both upstream: `labscript_utils/dict_diff.py:dict_diff` and
  `runmanager/__init__.py:dict_diff` (940-966).
- Differences:
  - labscript-utils tests only the first value for iterability and compares
    with `np.any(a != b)`.
  - runmanager tests either value and uses `np.array_equal`, which is
    upstream's 2014 fix that labscript-utils' copy never got.
  - On arrays of different lengths, or a scalar against an array,
    labscript-utils raises `ValueError` or calls them equal; runmanager reports
    a difference.
- Stays: labscript-utils' function, with runmanager's comparison and plain
  `dict`/`set` key handling, keeping the signature and adding no mode flag. It
  gave the same results as runmanager's on all 53 test cases.
- Core lines saved: 21, or a few more with the set handling.
- Consumer edits: runmanager deletes `__init__.py:940-966` and imports
  `labscript_utils.dict_diff`. The call at 1059 is unchanged.
- Visible to a user: yes, in lyse's public `Run.globals_diff` and
  `lyse.globals_diff`. They stop raising on a shape mismatch, and stop calling an
  all-zero array equal to 0. Keys print as `'a'` instead of `np.str_('a')`.
- Ian approved this, on 2026-10-09, together with the coupling it brings:
  - runmanager's `labscript_utils` floor (`pyproject.toml:34`,
    `labscript_utils>=3.3.0`) must rise to the version that carries the change;
  - no fork version number exists yet for that floor, and dependency floors
    are an open item.

### 11. Reading a TOML file

- Copies:
  - `labscript_profile.toml_config.load_toml_file`;
  - labscript-agents `config.py:loads` (6-24), a pass-through to
    `tomllib.loads` with one caller;
  - runmanager `globals_file.py:136-138`, the same `open` plus `tomllib.load`.
  labscript-optimization's `loads` validates into a `Config`, so it is not a
  copy.
- Differences: invalid UTF-8 raises `TOMLDecodeError` instead of
  `UnicodeDecodeError`.
- Stays: `load_toml_file`.
- Core lines saved: 20, of which 19 are in labscript-agents.
- Consumer edits:
  - labscript-agents: delete `config.py`, and `routine.py:39, 257-258` call
    `load_toml_file`;
  - runmanager: `globals_file.py:28, 136-138`.
- Visible to a user: no. labscript-optimization is unchanged: its config code
  must not depend on labscript-utils.

### 12. The event loop that Ctrl-C ends, and a QApplication made twice

- Copies, all upstream: the same five lines, a 500 ms timer plus a SIGINT
  handler that exits the loop, in runmanager `__main__.py:5625-5632`, lyse
  558-563 and runviewer 1776-1781. In addition:
  - runmanager (5616-5619) and runviewer (1758-1760) fall back to creating a
    `QApplication` that `Splash` has already made, so the fallback never runs;
  - runmanager repeats `configure_qapplication`'s `AA_DontShowIconsInMenus`
    line;
  - runviewer wraps `exec` in a one-call `execute_program`.
- Differences: none. blacs has no such loop, and adopting it there would change
  how Ctrl-C ends BLACS, so blacs is left out.
- Stays: `exec_qapplication(qapplication)` in the new `qtwidgets/application.py`
  of entry 4. It cannot go in `splash.py`, because runmanager's and runviewer's
  test fixtures stub that module with only `Splash`.
- Core lines saved: 16.
- Consumer edits: the lines above in the three `__main__` files, each taking the
  application from `splash.qapplication`.
- Visible to a user: no.

### 13. Choosing a readable text colour by contrast

- Copies:
  - blacs `plugins/progress_bar/__init__.py:black_has_good_contrast` (49-64),
    upstream;
  - runmanager `__main__.py:_relative_luminance` and `_contrast_ratio`
    (198-217), the fork's.
- Differences: both use WCAG relative luminance. Over 248,877 colours, blacs's
  rule equals choosing black or white by contrast ratio, with no mismatch. A
  deliberately wrong rule failed the same check.
- Stays: `contrast_ratio(a, b)` and `best_contrast(reference, candidates)` on
  `QColor`, in a new `qtwidgets/contrast.py`.
- Core lines saved: 14. After the new file's banner the saving is 1, so this is
  worth doing only in a module shared with other helpers.
- Consumer edits:
  - blacs: delete `progress_bar/__init__.py:49-64` and change 201-204;
  - runmanager: delete `__main__.py:198-217` and change 229-232.
- Visible to a user: no.

### 14. Reading properties from the connection table

- Copies, both upstream: `properties.py:_get_con_table_properties` (124-129) and
  `_get_unit_conversion_parameters` (132-137). Each also has an unused
  `import h5py`.
- Differences: only the column read.
- Stays: `properties.get`, with a two-entry map from location to column.
  Checked against a real HDF5 file.
- Core lines saved: 11.
- Consumer edits: none. The helpers are private, and `get` keeps its signature.
- Visible to a user: no.

### 15. `quad_monitor` and `quad_driver`

- Copies, both upstream: `unitconversions/quad_monitor.py` and
  `quad_driver.py`. They share `__init__`, `base_unit`, `derived_units` and the
  Gcm conversions.
- Differences: the driver clamps its current conversion and the monitor is
  linear; that stays per class. Both now share one mutable dict as a default
  argument.
- Stays: a private `_QuadConversion` base holding the shared parts, with a
  `None` default.
- Core lines saved: 11.
- Consumer edits: none.
- Visible to a user: no. Outputs are identical over eight inputs and four
  parameter sets.

### 16. `FileWatcher.add_files` and `add_folders`

- Copies, both upstream: `filewatcher.py:add_files` (208-224) and `add_folders`
  (226-244). They update the clean baseline the same way.
- Differences: none for the new files each adds.
- Stays: a private `_set_clean_modified_info`, called by both.
- Core lines saved: 10.
- Consumer edits: none.
- Visible to a user: no. The baseline maps matched before and after.

### 17. `_ensure_str`, defined four times

- Copies, all upstream and identical
  (`s.decode() if isinstance(s, bytes) else str(s)`):
  - blacs `front_panel_settings.py:27` and `plugins/progress_bar/__init__.py:44`;
  - labscript-utils `connections.py:25`;
  - runmanager `globals_file.py:46`.
  lyse and three labscript-devices files already import the private
  labscript-utils copy. Inline copies sit in runviewer (`__main__.py:479`,
  1573-1577, 1587), labscript-devices FunctionRunner, and lyse `asdatetime`.
- Differences: none.
- Stays: a public `ensure_str` in `labscript_utils/__init__.py`, beside
  `dedent`. It is public because three other repos already import it.
- Core lines saved: 10, or 4 without the inline copies. Ian's own example.
- Consumer edits:
  - labscript-utils: `connections.py:25-27` deleted, its uses renamed, and the
    no-op at 241 deleted.
  - blacs: `front_panel_settings.py:27-29, 88, 91, 107`;
    `progress_bar/__init__.py:44-46, 113, 192, 215`;
    `tests/test_front_panel_settings.py:14, 83-91`.
  - runmanager: `globals_file.py:46-47` and eleven uses.
  - lyse: `dataframe_utilities.py:22, 81, 83, 90, 92, 108`, and the dead branch
    at 57-58.
  - labscript-devices: `CiceroOpalKellyXEM3001.py:20, 616`;
    `NI_DAQmx/blacs_workers.py:30, 563, 654, 655, 819`;
    `PrawnBlaster/blacs_workers.py:19, 241`.
  - runviewer: `__main__.py:479, 1573-1577, 1587`.
- Visible to a user: no. A lab-local device that copied the private import
  would need the new name.

### 18. Reading a labconfig option with a default, two ways in `get_config`

- Copies: `ls_zprocess.get_config` (72-123, upstream) wraps each read in
  try/except. `ZMQClient.__init__` (283-296, the fork's) uses `fallback=`.
- Differences: none. The returned dict was identical for eight configs.
- Stays: `fallback=` throughout.
- Core lines saved: 9. This is as much style as duplication.
- Consumer edits: none.
- Visible to a user: no.

### 19. Error and question dialogs

- Copies, both upstream: lyse `utils/gui.py:error_dialog` and `question_dialog`
  take the application as an argument; runmanager
  `__main__.py:error_dialog` and `question_dialog` (260-269) read a module
  global.
- Differences: only where the parent window comes from. The title is the app
  name in both.
- Stays: `error_dialog` and `question_dialog` as methods of the
  `LabscriptGuiApplication` in entry 4.
- Core lines saved: 8.
- Consumer edits:
  - lyse: delete `utils/gui.py:23-31`; calls at `__main__.py:474`,
    `filebox.py:342` and `routines.py:247`.
  - runmanager: delete `__main__.py:260-269`; 21 calls become
    `app.error_dialog` or `self.error_dialog`.
- Visible to a user: no.

### 20. `ElidedLabelContainer.setElideMode` repeats the scroll area's checks

- Copies, both upstream: `qtwidgets/elide_label.py` 28-31 and 87-90. The same
  type check and refusal of `ElideMiddle`; the container then calls the scroll
  area, which checks again.
- Differences: none.
- Stays: the scroll area's checks.
- Core lines saved: 4.
- Consumer edits: none.
- Visible to a user: no.

### Considered, and proposed to leave

- `FreqConversion` against `NovaTechDDS9mFreqConversion`, 9 lines. Merging
  changes the last bit of `MHz_from_base` for about 30% of inputs.
- `ConnectionTable.find_by_name` as `self.table.get(...)`, 8 lines. It differs at
  the edges after `remove_device`, which blacs calls.
- `get_unit_conversion_class` against `import_class_by_fullname`, 4 lines.
  Sharing would make every sequence import `device_registry` and
  `labscript_devices`.
- `ConnectionTable.compare_to` against `Connection.compare_to`, about 10 lines.
  The two differ in logging, so a merge decides what is logged.
- `ConnectionTable.__init__`'s three log-and-raise handlers, about 8 lines; a
  merge changes the log.
- The child-process connection in lyse `analysis_subprocess.py` and runmanager
  `batch_compiler.py`. The shared part is the prescribed use of
  `ProcessTree.connect_to_parent()`, about 5 lines.
- `check_child_exited` in lyse and runmanager, about 12 lines. Each is tied to
  its own timer and output box, so a helper would be no smaller.
- `ShotQueueWidget.selected_ids` and `select_ids`. A shared helper saves no
  lines.
- `dedent` in zprocess. It is a different function, and zprocess cannot import
  labscript-utils.
- `setup_logging` in zprocess. It does a different job.
- The program launcher. It is already one implementation, `open_in_editor`.

### Totals

20 candidates hold 753 core lines. Entry 2 counts its new module's banner; the
others do not.
- inside labscript-utils (entries 2, 3, 7, 14, 15, 16, 18, 20): 250;
- across repos with one implementation in labscript-utils (entries 1, 4, 5, 6,
  8, 9, 10, 11, 12, 13, 17, 19): 503.

The new modules would be `lockable.py`, `application.py`, `leftclick.py`,
`file_dialogs.py`, `themed_window.py` and `contrast.py`, all in
`qtwidgets/`. Entries 4, 12 and 19 share one of them.

Decisions beyond the entries:
- whether labscript-utils should hold a GUI application layer (entries 4, 12,
  19);
- whether to widen the fork's difference from upstream for `__version__.py`
  (entry 1);
- whether lyse's Save menu, the Preferences tabs and `unitconversions.test` may
  change as described (entries 4, 7, 8).

### Seen for later steps

- **A bug, step 3:** `enumoutput.EnumOutput.set_EO` calls
  `self._EO.remove_widget(self, False)`, but blacs's `EO.remove_widget` takes one
  argument.
  - Run against blacs Development: moving an `EnumOutput` to a second `EO`
    raises `TypeError: EO.remove_widget() takes 2 positional arguments but 3
    were given`.
  - The same line is on upstream `master`.
  - It is latent: blacs's only caller, `EO.add_widget`, hands over a fresh
    widget, and nothing moves a widget between `EO`s.
- **Step 3, other bugs and guards:**
  - `FreqConversion` and `NovaTechDDS9mFreqConversion` append to a class-level
    `derived_units` list on every instantiation.
  - The quad conversions share one mutable dict as a default argument.
  - The apps' `required_params` still demand the program keys, although
    `open_in_editor` now handles a missing program with a dialog.
  - runmanager's `batch_compiler` connects to its parent at import, which is why
    its docs mock `connect_to_parent`.
- **Step 4, dead code and pass-throughs:**
  - `ConnectionTable.assert_superset`, with `Connection.diff` and an import:
    about 40 lines, no caller.
  - The `ls_zprocess` one-line forwarders `zmq_get*`, `zmq_push*`, `Event` and
    `Handler`: 20 lines. Callers: runmanager `__init__.py:35, 881, 919`, blacs
    `progress_bar/__init__.py:32, 85`, and `setup_logging.py:17, 52`.
  - `_resolve_appconfig_save_path`. Entry 3 of step 1 was kept, so
    `_resolve_appconfig_load_path` is not the same call after all.
  - The `if type(x) is tuple` unwraps after file dialogs, at about 25 sites; see
    entry 6.
  - The `fingertab.py` demo.
  - lyse's `get_check_state` binding shim.
  - runmanager's `get_shot_globals` forwarder and its unused `dedent` import.
- **For other owners:**
  - labscript-agents keeps unused copies of labscript-optimization's routine
    plumbing, 242 lines, on purpose according to its plan.
  - labscript-agents imports labscript_utils unconditionally, in `relay.py:28-29`
    and `server.py:31`, but lists it only under its `lyse` extra.
  - runmanager starts runviewer by hand rather than with
    `zprocess.start_daemon`, whose `os.fork()` is the reason; that is the zprocess
    session's to fix.
  - blacs's `shot_execution.tempfilename` duplicates the stdlib's `tempfile`.
  - `docs/source/conf.py` boilerplate is copied in eight repos (step 5).
  - zprocess's zlock and zlog servers share code.

## On merge

These describe Development, which still holds the code step 1 removed. Whoever
merges CodeHealth into Development updates them in the meta repo:

- `issues/server_interfaces_2026_09_25.md:112-113` lists `LinkIndicator`'s
  `interval=2` argument, now an attribute.
- `issues/blacs_issues_2026_08_28.md`, slice 11 (lines 294-306, 320), plans to
  silence plugin deprecation warnings that are gone.
- `issues/seen_while_mapping.md:40` names the duplicated `_is_accepted_path`,
  now removed.
- `CODEX.md:961-964` lists "icons" among `MenuContext`'s features.
- `labscript_project.md:97` says `qtwidgets/__init__.py` lazily re-exports the
  shot queue widget.
