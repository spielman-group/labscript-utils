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
- Outcome: done: labscript-utils c4ecaec; labscript 4a9dcde, labscript-devices
  f986065, runmanager 538ce6c, blacs 769a004, lyse 0bc790d, runviewer a5ef546,
  labscript-suite 62a725f. No repository's packaging read __version__.py.

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
- Outcome: done in labscript-utils, f76d464: 72 lines saved, with full
  docstrings on the new public names. No consumer edits.

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
- Outcome: done in labscript-utils, 18cde67; with entry 18, 63 lines saved. No
  consumer edits.

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
- Visible to a user: yes, in small ways.
  - lyse's Save item follows a Save as, which it does not do today.
  - lyse's Load prompt said "which groups are active/open", wording copied from
    runmanager; it now says "which scripts are loaded", as lyse's quit prompt
    does.
  - lyse's "no changes to revert" and "Dataframe is empty" warnings used to raise
    AttributeError, since `Lyse` has no `self.app`; they now show.
- Decision for Ian: whether labscript-utils should hold a GUI application layer
  at all. Entries 12 and 19 share the same new module.
- Optional, about 17 more lines: the "save changes?" Yes/No/Cancel prompt
  appears four times (lyse 232, 340; runmanager 2512, 4385). One method could
  serve all four, but the wording differs per app.
- Outcome: labscript-utils f0b294a, with save_configuration on
  LabscriptApplication since 4e50a77; lyse keeps its own Load prompt through
  config_description. Consumers: lyse 7e96ae4, runmanager 9877b45, runviewer
  4db574e (save_configuration only, keeping LabscriptApplication).

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
- Outcome: labscript-utils 62e8323. Consumers: lyse 7e96ae4, runmanager 9877b45.

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
- Outcome: labscript-utils d90310a; the application layer's two dialogs use it
  too. blacs's five dialogs built as `QFileDialog` objects (`__main__.py` load
  and save front panel, and three in `plugins/connection_table`) use it as well,
  27 sites in all; they lose only the detail view of Qt's own dialog where the
  native one is not used. Consumers: runmanager 9877b45, lyse 7e96ae4, runviewer
  4db574e, blacs 20aabd4.

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
- Outcome: done in labscript-utils, 7da8765.

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
- Outcome: reversed by Ian's decision: finger tabs are not standard for a
  configuration dialog. labscript-utils fb7909c gives the Preferences dialog a
  plain QTabWidget, runmanager 26a7777 takes its three classes back, and the
  the commit after deletes `qtwidgets/fingertab.py`.

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
- Outcome: labscript-utils 7404602. Consumers: lyse 7e96ae4, blacs 20aabd4,
  runmanager 9877b45.

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
- Outcome: done: labscript-utils 789ed7a, runmanager 5db8175. The review notes
  two further differences from the old labscript-utils copy, both runmanager's
  long-standing behaviour: equal nested lists of uneven lengths now compare
  different, and a tuple and an equal list compare equal. runmanager's
  labscript_utils floor stays until a fork version exists; dependency floors are
  an open item.

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
- Outcome: done: runmanager 5db8175, labscript-agents c0a1ed2 (and fb9ca7b,
  labscript_utils as a required dependency). No labscript-utils change.

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
- Outcome: labscript-utils f0b294a. Consumers: lyse 7e96ae4, runmanager 9877b45,
  runviewer 4db574e. lyse 83cfd6c also runs each worker's event loop with
  `exec_qapplication`, so Ctrl-C and zprocess's SIGTERM now end idle workers.

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
  `QColor`, in a new `qtwidgets/contrast.py` (built in `themed_window.py`, by
  Ian's decision).
- Core lines saved: 14. After the new file's banner the saving is 1, so this is
  worth doing only in a module shared with other helpers.
- Consumer edits:
  - blacs: delete `progress_bar/__init__.py:49-64` and change 201-204;
  - runmanager: delete `__main__.py:198-217` and change 229-232.
- Visible to a user: no.
- Outcome: labscript-utils 3a7d146, in themed_window.py by Ian's decision.
  Consumers: blacs 20aabd4, runmanager 9877b45; at an exact tie blacs now picks
  black text where it picked white, which no real colour reaches.

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
- Outcome: done in labscript-utils, bf751f5.

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
- Outcome: done in labscript-utils, 98dca62; 8 lines saved, the quad defaults no
  longer shared between instances.

### 16. `FileWatcher.add_files` and `add_folders`

- Copies, both upstream: `filewatcher.py:add_files` (208-224) and `add_folders`
  (226-244). They update the clean baseline the same way.
- Differences: none for the new files each adds.
- Stays: a private `_set_clean_modified_info`, called by both.
- Core lines saved: 10.
- Consumer edits: none.
- Visible to a user: no. The baseline maps matched before and after.
- Outcome: done in labscript-utils, 2c6dab7.

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
- Outcome: done: labscript-utils d784002, and 3c6e2d3 removes connections'
  interim alias; blacs 268ac41, runmanager 9877b45, lyse 7e96ae4, runviewer
  4db574e, labscript-devices d081fa2 (FunctionRunner's inline copy too).

### 18. Reading a labconfig option with a default, two ways in `get_config`

- Copies: `ls_zprocess.get_config` (72-123, upstream) wraps each read in
  try/except. `ZMQClient.__init__` (283-296, the fork's) uses `fallback=`.
- Differences: none. The returned dict was identical for eight configs.
- Stays: `fallback=` throughout.
- Core lines saved: 9. This is as much style as duplication.
- Consumer edits: none.
- Visible to a user: no.
- Outcome: done in labscript-utils, ba12b35.

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
- Outcome: labscript-utils f0b294a. Consumers: lyse 7e96ae4, runmanager 9877b45.

### 20. `ElidedLabelContainer.setElideMode` repeats the scroll area's checks

- Copies, both upstream: `qtwidgets/elide_label.py` 28-31 and 87-90. The same
  type check and refusal of `ElideMiddle`; the container then calls the scroll
  area, which checks again.
- Differences: none.
- Stays: the scroll area's checks.
- Core lines saved: 4.
- Consumer edits: none.
- Visible to a user: no.
- Outcome: done in labscript-utils, 0aeaa63.

### Outcome

All twenty entries are done. labscript-utils' side is 789ed7a..3c6e2d3, with
review fixes in 4e50a77, 063ec31 and 3752d13. Every consumer's suite passes on
its CodeHealth against labscript-utils 3c6e2d3: runmanager 139, blacs 69, lyse
44, labscript-devices 43, labscript-agents 15, runviewer 10, labscript 3, and
hyde's 17 plugin-related test files. Non-blank code lines across the suite:
labscript-utils +230, which holds the shared code now; runmanager -401, lyse
-218, blacs -75, runviewer -48, labscript -24, labscript-devices -25,
labscript-agents -19, labscript-suite -24; 604 fewer in all, and 12 fewer test
lines.

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
`file_dialogs.py` and `themed_window.py` (which holds the contrast functions), all in
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
- **From the final review, for later steps:**
  - Step 3, for runmanager now that the finger tabs are back there:
    `FingerTabWidget.setTabClosable(i, False)` on a tab with a close button
    raises TypeError in `FingerTabBarWidget.setTabButton`; no caller does it yet.
  - Step 4: blacs keeps a one-call `execute_program` around `exec`, which drops
    the exit code (`__main__.py:692-695`).
  - Step 2 leftovers, for the owners: runmanager's and lyse's quit prompts repeat
    the text of their `config_description` and the shared Yes/No/Cancel block;
    blacs `connection_table/__init__.py:432` and runviewer `__main__.py:755`
    normalise paths the dialogs already return absolute.
  - Every suite package now imports `labscript_utils.versions.package_version`,
    and labscript-agents uses `labscript_profile.toml_config`, so their
    labscript_utils floors must rise with the dependency-floor item.
  - The installed setuptools_scm warns that `release-branch-semver` is renamed;
    `package_version` and each repo's pyproject are the places to change it.
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

## Step 3: root causes

"Each guard added since the fork is traced to its cause, and fixed there where
the cause is real." A guard is a check, try/except, isinstance or hasattr test,
fallback, retry, coercion or workaround around a symptom.

How the candidates were found:
- the step 3 notes in this file;
- a sweep of all 209 fork commits (`git log master..CodeHealth`), reading every
  fix commit's message and diff;
- `git blame` of every guard-shaped line that survives.

How they were checked:
- Refs: labscript-utils `CodeHealth` at a885dec, the other repos at `CodeHealth`,
  zprocess and hyde at `HEAD`.
- Each symptom was shown by running, in a scratch copy, with the guard removed or
  with the bad input, except where an entry says otherwise.
- Every caller search ran over every repo, tests included, beside a control that
  matches.

### 1. excepthook's hook calls `Logger.warn`, so six repos' tests silence warnings

- Guard: nine `with warnings.catch_warnings(): warnings.simplefilter('ignore')`
  blocks around imports in other repos' tests:
  - blacs `tests/fixtures.py:73-81`;
  - runviewer `tests/fixtures.py:79-85`;
  - runmanager `tests/fixtures.py:85-91`;
  - lyse `test_analysis_subprocess.py`, `test_filebox.py`, `test_main_window.py`
    and `test_multishot_paths.py`;
  - labscript-optimization and labscript-agents `tests/test_lyse_routine.py`.
  All were added between 2026-09-01 and 2026-10-05. The blacs, runviewer and
  runmanager blocks state the reason.
- Symptom: with `excepthook.set_logger()` installed and pytest's filters, any
  warning raises `RecursionError`. The cause is
  `labscript_utils/excepthook/__init__.py:logwarning` (line 92): a
  `warnings.showwarning` hook calling `l.logger.warn`, which warns in turn.
  - Shown: `RecursionError` on CodeHealth and on `master`;
  - with `.warn` changed to `.warning`, it runs clean.
  - Default filters ignore that DeprecationWarning, so a real application run is
    unaffected.
- Cause: labscript-utils, one word, and upstream's.
- Proposal: change `.warn` to `.warning`. Then each owner tries its blocks without
  the wrapper.
  - The recursion certainly reaches blacs and runviewer, which call `set_logger`
    at import.
  - In runmanager, lyse, labscript-optimization and labscript-agents nothing calls
    it at import, so the reason given there does not hold by grep; each owner
    tests the removal.
- Core lines: guard 44 across six repos; the fix changes 1.
- Visible to a user: no.
- Owners: labscript-utils (the fix); blacs and runviewer (wrappers, confirmed);
  runmanager, lyse, labscript-optimization and labscript-agents (to test).
- Upstream: yes, on `master`; the fix also goes to UpstreamBugFixes.

### 2. runmanager's `batch_compiler` connects to its parent at import, and its docs mock that

- Guard:
  - `runmanager/batch_compiler.py` lines 15-21: `ProcessTree.connect_to_parent()`
    and its aliases at module level;
  - the 26-line mock of `connect_to_parent` in runmanager's
    `docs/source/conf.py:74-102`, from 1e3a618 (2020).
  Both are upstream's.
- Symptom: importing `runmanager.batch_compiler` outside a process tree raises
  `RuntimeError: No ZPROCESS_PARENTINFO environment variable found`, which is why
  the autosummary needs the mock.
- Cause: runmanager makes the connection at module level instead of in its
  `__main__` block, where lyse's `analysis_subprocess.py` makes the same one.
  `compile` also reads the module global `kill_lock` instead of
  `self.kill_lock`.
- Proposal: connect inside the `__main__` block and pass the three attributes to
  `BatchProcessor`, which already takes them. Use `self.kill_lock`, and delete
  the docs mock.
  - Shown: the patched module imports with no parent.
  - A real compile through the original and the patched child gives the same
    result: a good script succeeds, with the same nine shot-file groups, and a
    failing script fails.
- Core lines: guard 32; the fix moves 3 lines, edits 2 and deletes 26.
- Visible to a user: no.
- Owners: runmanager.
- Upstream: the same code on `master`; a design wart, not a bug.

### 3. Case-insensitive section names in `TomlConfigParser`

- Guard: `labscript_profile/toml_config.py:TomlConfigParser._canonical_section_name`,
  and the overrides that pass every section argument through it: `add_section`,
  `has_section`, `options`, `has_option`, `remove_section`, `remove_option`,
  `__getitem__`, `get` and `items`. From 806fab5 and 7a623ba (2026-03).
- Symptom: `LabConfig().get('DEFAULT', ...)` and `has_section('BLACS/plugins')`,
  upstream's spellings, reach the lower-case tables. Without the guard they raise
  `NoSectionError`.
- Cause: no caller in any repo still uses an upper-case section. The same search
  on blacs `master` matches, so it can fail. It serves only lab-local scripts and
  user TOML written against upstream's names, which no search reaches.
- Proposal: keep, for Ian to decide. It is the one place where upstream's public
  usage still runs, and AGENTS.md asks that user scripts keep working.
- Core lines: guard 32. Dropping it also changes 1 line in each of `read_toml`,
  `set` and `LabConfig.__init__`.
- Visible to a user: only to a lab-local script or labconfig that spells a section
  in upper case.
- Owners: none.
- Upstream: not applicable.

### 4. Brace escaping in `lookup_format`, so one formatting pass can feed the next

- Guard: `labscript_utils/lookup_format.py`: `_escape_braces`, `unescape_braces`
  and `_LookupFormatter.produces_template`, with their uses in `format` and the
  docstring paragraph. From 650646d and a220994 (2026-08-28). runmanager's
  `__main__.py:3585` also calls `unescape_braces`, for display.
- Symptom: runmanager formats its output templates in two passes:
  `new_sequence_details` with `preserve_unresolved_roots=('globals',)`, then
  `make_run_files` per shot.
  - Shown before 650646d: a literal brace in a template, or in the script name,
    makes pass 2 raise.
  - On CodeHealth, both passes work.
- Cause: runmanager's design, in which the first pass returns half-formatted text
  that the second parses again. Only runmanager calls these functions.
- Proposal: low confidence, and runmanager's decision. Format once per shot:
  `new_sequence_details` returns the two templates and `now`, and `make_run_files`
  calls `format_lookup_string` once with the shot's globals. The escaping and
  `produces_template` then go.
  - This matches the settled rule that the labconfig templates are formatted once
    per shot.
  - It changes two public functions of runmanager, and how runmanager's window
    shows the default output folder.
  - If the two-pass design stays, keep this code.
- Core lines: guard about 28 here and 2 in runmanager; the fix changes about 6 in
  runmanager.
- Visible to a user: no. Braces work either way.
- Owners: runmanager first; labscript-utils removes its side after.
- Upstream: no; `lookup_format.py` is the fork's.

### 5. The old hook name is asked first in `PluginManager._get_plugin_event_handlers`

- Guard: the `get_callbacks`-before-`get_event_handlers` order, from 23571b2
  (2026-10-08). BasePlugin defines both names, so `hasattr` is true for both and
  an order has to be chosen.
- Symptom: in the other order, a BasePlugin subclass overriding only
  `get_callbacks` is silently dropped. Shown in scratch: three plugin shapes give
  three handlers on CodeHealth, and two with the order reversed.
- Cause: one hook with two names. blacs's 7 plugins still define `get_callbacks`.
  labscript-utils keeps `BasePlugin.get_callbacks` and
  `PluginManager.get_callbacks` as aliases. No plugin defines both.
- Proposal: fix the cause. blacs renames its 7 methods to `get_event_handlers`;
  labscript-utils then drops both aliases and the ladder, leaving one `getattr`.
  This is step 4's compatibility leftover; step 3 adds that this order is its
  symptom.
- Core lines: guard 10, or 28 with the two aliases it serves. The fix is 7
  renames in blacs and about 25 lines fewer here.
- Visible to a user: yes, to a lab plugin written for upstream blacs, which
  defines only `get_callbacks`: it loses its event handlers. Such plugins are
  deliberately unsupported (Ian, 2026-10-11).
- Owners: blacs, then labscript-utils.
- Upstream: no; upstream blacs has only `get_callbacks`.

### 6. `PluginManager._setup_action_args` keeps the legacy no-argument `plugin_setup_complete()`

- Guard: `labscript_utils/plugins.py:PluginManager._setup_action_args` (27 lines)
  and its call. From 4cf6f52 (2026-08-28), which replaced upstream's retry; that
  is blacs e3e5d2f on its UpstreamBugFixes.
- Symptom:
  - Before 4cf6f52, a hook that raises after a side effect ran twice. Shown at
    4cf6f52^.
  - On CodeHealth it runs once.
  - A legacy `plugin_setup_complete(self)` runs once, with a warning.
- Cause: the pre-`data` legacy form. No plugin anywhere uses it: all seven blacs
  plugins take `BLACS`, and hyde uses setup activities. Only a labscript-utils
  test defines one.
- Proposal: drop the legacy form, together with step 4's "no-argument fallback"
  item. `setup_complete` then calls `action(data)` once; a failing hook still runs
  only once.
- Core lines: guard 28, plus a 13-line test.
- Visible to a user: yes, to a lab plugin with upstream's no-argument
  `plugin_setup_complete()`: it logs an error, and its setup step does not run.
  Such plugins are deliberately unsupported (Ian, 2026-10-11).
- Owners: labscript-utils.
- Upstream: the retry's double run is upstream's bug, and its fix is already
  offered.

### 7. The plugin enable-flag guard in `PluginManager.discover_modules`

- Guard: the `try: getboolean ... except ValueError:` block (16 lines). From
  35b76df (2026-08-28) and 16c2e0b (2026-10-07); the first is the counterpart of
  blacs 87c3774, on its UpstreamBugFixes.
- Symptom:
  - With the guard, a plugin directory named like a labconfig default key, and a
    hand-typed `theme = 1`, both start with a warning.
  - Without it, each raises `ValueError: Not a boolean: …`, naming no plugin.
  Both shown with a real `LabConfig`.
- Cause, two parts:
  - configparser's `[default]` inheritance makes a default key look like a flag.
    That bites only if a plugin directory has a default key's name, and none of
    blacs's seven does.
  - A hand-typed non-boolean flag, which is a user error.
- Proposal: Ian decides.
  - Preferred: drop the block, so a bad flag stops BLACS at start-up like any other
    malformed labconfig value.
  - Alternative: keep it as per-plugin containment, shrunk to a warning and the
    default state, about 5 lines.
  - `toml_config`'s two `getboolean` lines stay either way.
- Core lines: guard 16; the fix deletes 15 or keeps about 5. A 19-line test goes,
  or is rewritten.
- Visible to a user: yes. A bad flag stops BLACS at start-up with a traceback
  instead of a log warning.
- Owners: labscript-utils.
- Upstream: the collision defect is on blacs `master`, and its fix is already
  offered.

### 8. `ZMQServer.handler`'s reply checks

- Guard: `labscript_utils/ls_zprocess.py:ZMQServer.handler` lines 210-226:
  - `except BaseException`;
  - the pickle round-trip test;
  - the `__main__`-class test;
  - the `RuntimeError` stand-in.
  From 55afd10, df35bd4 and 154f534 (2026-09-25).
- Symptom, shown with a real server and client in separate processes, on zprocess
  at HEAD. With the guard, each case below reaches the client as a `RuntimeError`
  carrying the message:
  - an exception holding something unpicklable: without the guard, the server
    shows its own error dialog and the message is lost;
  - an exception class defined in the server's `__main__`: the client raises
    `AttributeError`;
  - an exception with a custom `__init__`: the client raises `TypeError`;
  - a `SystemExit` in a handler: it ends zprocess's mainloop, and every later
    request times out.
- Cause, three parts:
  - zprocess pickled the reply outside its `try`. That is fixed by zprocess
    6c31b8f, which is unreleased, and labscript-utils floors `zprocess>=2.18.0`.
  - zprocess's `except Exception` lets `SystemExit` through.
  - pickle rebuilds classes by reference and exceptions through `cls(*args)`.
    That is stdlib behaviour, outside our reach.
- Proposal: keep the guard.
  - Ask the zprocess session to catch `BaseException` in `ZMQServer.mainloop`,
    which would simplify two lines here.
  - Ask it to add 6c31b8f to its UpstreamBugFixes.
  - Fix the 3-line comment at `ls_zprocess.py:212-214` now: it is false at zprocess
    HEAD.
- Core lines: guard 15; the comment 3.
- Visible to a user: yes, without the guard: a client gets an unpickling error or
  a timeout instead of the server's message.
- Owners: labscript-utils for the comment; zprocess for the rest.
- Upstream: zprocess `master` pickles outside the `try`, an upstream bug.

### 9. `FreqConversion` and the NovaTech conversions append to `derived_units` in `__init__`

- Guard: the `if hasattr(self, 'derived_units'): … append … else: …` branch, at
  three sites:
  - `generic_frequency.FreqConversion`;
  - `NovaTechDDS9mFreqConversion`;
  - `NovaTechDDS9mAmpConversion`.
  All upstream's, identical on `master`.
- Symptom: nothing in the suite is affected; each instance gets its own list.
  Shown: a lab's subclass that declares `derived_units` at class level grows that
  class list by three entries with every instance.
- Cause: `.append` on what can be the class's list. Upstream's, and latent.
- Proposal: leave it. If Ian wants it closed, write
  `self.derived_units = [*getattr(self, 'derived_units', []), 'MHz']` at each
  site; results in the suite are the same.
- Core lines: guard 12; the optional fix changes them to 3.
- Visible to a user: only through such a lab subclass, as repeated units.
- Owners: labscript-utils.
- Upstream: yes, latent; not worth offering unless Ian wants it.

### 10. The apps still require the `[programs]` labconfig keys

- Guard: the `programs` entries of each app's `required_params`:
  - runmanager `__main__.py`, 3 lines;
  - blacs `__main__.py:654-659`, 1 line;
  - lyse `__main__.py`, 4 lines.
  `LabConfig` enforces them. All three are upstream's, where the apps read the
  keys themselves.
- Symptom: shown with a labconfig lacking `[programs]`:
  - `LabConfig` refuses, with "does not have the required keys";
  - without those entries it starts;
  - `open_in_editor` then shows its own dialog for the missing program.
- Cause: the requirement is stale. The fork moved every reader to
  `labscript_utils.text_editor.open_in_editor`, which handles a missing program
  itself.
- Proposal: delete the eight entries.
- Core lines: guard 8; all of it goes.
- Visible to a user: yes. An app whose labconfig lacks `[programs]` now starts,
  and its Edit or Open button shows a dialog, where today the app refuses to
  start.
- Owners: runmanager, blacs, lyse.
- Upstream: required correctly there; not a bug.

### 11. `Splash.update_text` waits for a paint only while the window is exposed

- Guard: `labscript_utils/splash.py:Splash.update_text`, the `isExposed()` test
  (5 lines). From 0811a4c (2026-10-04); also offered as c8303fa on UpstreamBugFixes.
- Symptom:
  - Shown offscreen: upstream's `update_text` before `show()` waits forever, and
    CodeHealth's returns.
  - A splash covered by another window on macOS stalls start-up until it is
    brought forward. That comes from the commit message; it needs a real macOS
    window server.
- Cause: macOS paints no covered window, outside our reach, meeting upstream's
  wait for a paint that may not come.
- Proposal: keep. `self.repaint()` might replace the whole wait, but that needs a
  run on a Mac.
- Core lines: guard 5.
- Visible to a user: yes, without it: the stall.
- Owners: none.
- Upstream: yes, the loop is upstream's, and the fix is offered.

### 12. `LinkIndicator` asks through a client of its own

- Guard: `labscript_utils/qtwidgets/link_indicator.py:LinkIndicator.__init__`,
  its private `ZMQClient` and the docstring sentence. From 29f21db (2026-10-05).
- Symptom:
  - Shown: two threads sharing one zprocess client deadlock for good on zprocess
    before 162afe7, with 0 of 8 threads finishing in 480 s.
  - After 162afe7, 8 of 8 finish in 2.3 s.
- Cause: zprocess's Interruptor waited for an acknowledgement XPUB never sends.
  Fixed by zprocess 162afe7, which is not on zprocess `master` or in any release
  labscript-utils' floor allows.
- Proposal: keep until the zprocess floor carries 162afe7, then drop the
  docstring sentence. The workspace rule of one client per thread then no longer
  rests on this deadlock; whether to keep it is Ian's.
- Core lines: guard 4.
- Visible to a user: no.
- Owners: zprocess, for a release.
- Upstream: the zprocess bug is on its `master`.

### 13. `labscript-profile-create -c` compiles into a file with no `globals` group

- Guard: `labscript_profile/create.py:compile_connection_table`, which writes
  `with h5py.File(output_h5_path, 'w'): pass`. From 805d94e (2026-03-25, "Fix TOML
  globals profile bootstrap"). It replaced upstream's
  `runmanager.new_globals_file(output_h5_path)`.
- Symptom: a real bug.
  - The compile's `labscript_init` reads `f['globals']` through
    `get_shot_globals`, and the empty file has none. Shown by emulating the batch
    compiler on the profile's example connection table: `KeyError: … 'globals'`.
  - With the group, the compile succeeds.
  - The command still prints "Output written to …" and leaves an empty
    `connection_table.h5`.
- Cause: the same day, runmanager's `new_globals_file` began writing TOML, and
  805d94e swapped in an empty HDF5 file without running a compile. The cause is in
  labscript-utils.
- Proposal: fix the cause:
  `with h5py.File(output_h5_path, 'w') as f: f.create_group('globals')`.
  Optionally, runmanager's `compile_labscript_async` docstring (`__init__.py:818`)
  stops pointing at the TOML `new_globals_file`.
- Core lines: guard 4; the fix changes 2, net 0.
- Visible to a user: yes. Profile creation with `-c` works again.
- Owners: labscript-utils; optionally runmanager for its docstring.
- Upstream: no; a regression the fork made.

### 14. runmanager's `FingerTabWidget.setTabClosable(i, False)` raises TypeError

- Guard: `runmanager/__main__.py:FingerTabBarWidget.setTabButton` rejects anything
  that is not a `TabToolButton`, `None` included. Upstream's (88980c8, 2014),
  identical on runmanager `master`.
- Symptom: shown offscreen. On a tab with a close button,
  `setTabClosable(i, False)` raises
  `TypeError: Not a TabToolButton, won't paint correctly`. The only caller,
  `addTab`, never reaches that branch.
- Cause: the guard rejects the `None` that Qt allows for removing a button.
- Proposal: let the guard allow `None`, in 2 edits, or delete the unreachable
  removal branch, 4 lines.
- Core lines: guard 4; the fix changes 2.
- Visible to a user: no.
- Owners: runmanager.
- Upstream: yes, latent. It could go on runmanager's UpstreamBugFixes.

### 15. `EnumOutput.set_EO` passes `remove_widget` a second argument

- Guard: none; it is a bug. `labscript_utils/qtwidgets/enumoutput.py:set_EO` calls
  `self._output.remove_widget(self, False)`, but blacs's `EO.remove_widget(widget)`
  takes one argument. It was copied from AnalogOutput in 5810137 (2019).
- Symptom: shown with blacs's real `EO`. Moving an `EnumOutput` to a second `EO`
  raises `TypeError`, and leaves the widget in both `EO`s' lists. Without
  `, False`, the move works.
- Cause: labscript-utils, a copy-paste from AnalogOutput.
- Proposal: drop `, False`.
- Core lines: guard 0; the fix changes 1.
- Visible to a user: no. Nothing moves a widget between `EO`s.
- Owners: labscript-utils.
- Upstream: yes, on labscript-utils and blacs `master`, and latent. The fix also
  goes to UpstreamBugFixes.

### Outcome

Ian approved the coordinator's recommendation. Every commit below is on
CodeHealth unless named otherwise, and none is merged or pushed.
- Fixed at the cause:
  - 1: labscript-utils b3c738c, and UpstreamBugFixes e08fbe6. Every wrapper
    went: blacs 2f238e0, runviewer 0ec3be3, runmanager 74ba647, lyse 010cd03,
    labscript-optimization e22dd23 and labscript-agents e07f88d.
  - 2: runmanager 74457a7.
  - 5: blacs dee664a renamed its seven hooks, then labscript-utils d515339
    dropped the aliases and the ladder.
  - 6: labscript-utils 2cf4b3b. 7: ed279d6, so a malformed flag stops start-up.
  - 10: runmanager a8fcadb, blacs 514982e and lyse 010cd03.
  - 13: labscript-utils 85ce0b9. runmanager's docstring was left.
  - 14: runmanager 20ee516, and its UpstreamBugFixes 96ff041.
  - 15: labscript-utils dba97b0, and UpstreamBugFixes 086a267.
- Kept: 3, 8, 9, 11 and 12, as proposed, and 4.
  - 4: runmanager declined it on Ian's point, so the escaping stays. Every shot of
    a sequence carries the date the sequence started, which the two passes give
    by construction. runmanager 2e19640 says so where the date is formatted.
  - 8: the comment is fixed in 081aac5, and the guard stays. zprocess catches
    `BaseException` in 51adae8, also on its Production and UpstreamBugFixes, and
    its UpstreamBugFixes holds 6c31b8f's fix and 162afe7's. Two lines here can go
    once the zprocess floor passes a release holding them, as with entry 12.
- The shared-secret check (635aea9) stays; load_appconfig's comment is two lines,
  in a17e2b5.
- Removing the warning wrappers showed setuptools_scm's rename of the
  `release-branch-semver` scheme. Ian chose the new name,
  `semver-pep440-release-branch`, which needs setuptools_scm 10. Every repo uses
  it and requires setuptools_scm>=10:
  - labscript-utils 998b983, zprocess dd92777, runmanager 169056a;
  - blacs fabe2da, lyse 2aa9328, runviewer b39a93e, labscript e1e3d40;
  - labscript-devices bf6d896, labscript-agents 68c2dab;
  - labscript-optimization 3d633bc, labscript-suite 07e6e15.
- Every consumer's suite passes on its CodeHealth against labscript-utils d515339
  and zprocess 51adae8: runmanager 139, blacs 69, lyse 44, labscript-devices 43,
  labscript-agents 15, runviewer 10, labscript 3, labscript-optimization 216, and
  hyde's 17 plugin-related test files.
- Non-blank lines, code then tests: labscript-utils -74 and -46; runmanager -28
  and -8; lyse -4 and -12; blacs -1 and -10; runviewer, labscript-optimization
  and labscript-agents 0, and -8, -3 and -3. In all, 107 fewer code lines and 90
  fewer test lines.

### Decisions for Ian beyond the entries

- **`get_config`'s shared-secret check (635aea9, on UpstreamBugFixes).** It
  fixes upstream's misplaced check at its cause, but it changes behaviour.
  - On `master`, an explicit `allow_insecure = False` with no secret file still
    starts. On CodeHealth it raises at start-up.
  - zprocess enforces the rule only per connection, so a loopback-only lab ran on
    `master`.
  - No shipped config sets `allow_insecure = False`.
  - The commit was kept separate so that it could be dropped.
- **`as_config_list`'s TOML-array form (679bb78).** It is already the
  cause-level fix of a real cause, so keep it. Without it, a TOML array in
  `userlib` raises at every Python start, shown by running.
- **`load_appconfig`'s `default` table (a54da76).** It removed a guard, so none is
  left. Its 4-line comment can shrink to 2.
  - A side note: `isinstance(section, dict)` silently drops a top-level scalar
    from a hand-edited app config.

### Totals

15 entries; their guards hold 262 core lines.
- **To fix at the cause, or drop:** entries 1, 2, 5, 6, 7, 10, 13, 14 and 15, and
  entry 4 if runmanager agrees. These hold 194 lines.
  - Two are real bugs: 13, a regression the fork made, and 15, an upstream bug.
  - Entries 1, 14 and 15 are upstream bugs, and their fixes can also be offered
    upstream.
- **To keep, the cause being out of reach or already the right fix:** entries 3,
  8, 9, 11 and 12. These hold 68 lines.
  - Entry 8 needs only its comment fixed.
  - Entry 12 can go once the zprocess floor rises.

Owners who would make a change: runmanager (2, 4, 10, 13's docstring, 14); blacs
(1, 5, 10); lyse (1, 10); runviewer, labscript-optimization and labscript-agents
(1); zprocess (8, 12).

### Seen for later steps

- `TomlConfigParser.read_toml`'s first `isinstance(data, dict)` check can never
  fail, since `tomllib` always returns a dict. Step 4.
- `get_default_appconfig_file`'s `except (NoOptionError, NoSectionError)`: the
  `default` section never raises `NoSectionError`, so half the tuple is dead.
  Step 4.
- `properties._default`'s numpy branches could be one `isinstance(o,
  np.generic)` returning `o.item()`, saving 2 lines. Step 6.
- `configure_qapplication`'s `_labscript_qapplication_configured` property is a
  darwin detail with a dead branch, 3 lines. Step 4.

## Step 4: dead code and compatibility leftovers

"An old interface kept for compatibility, whose remaining users are all in the
suite, goes, and its users move to the new one. Deciding that a name is unused
means searching every repo, hyde included."

How the candidates were found:
- the step 4 notes in this file;
- the labscript-utils sections of the meta repo's `issues/seen_while_mapping.md`;
- a sweep of all 661 names defined in labscript-utils, counting each one's
  tokens in every file of every repo. A name found only where it is defined is
  a candidate. A second pass counted code tokens only and resolved imports,
  which finds a name hidden by prose or by a common word.

How they were checked:
- Refs: labscript-utils `CodeHealth` at e8e3f72, which all line numbers below
  refer to. The other repos at `CodeHealth`, and desktop-app and
  labscript-c-extensions at `HEAD`: 14 repos.
- Each search is a whole-word `git grep` in all 14 repos, giving each repo's
  exit status. "No caller" means exit 1 in 13 repos, and a hit at the definition
  only in labscript-utils.
- Each search ran beside a control that matches, named in its entry.
- The sweep was checked both ways. A used name, `get_event_handlers`, counts 58
  tokens against 2 definitions. An unused one, `add_folder`, counts 1 against 1.
- Every name's presence on `master` was checked. Such a name is published API
  that lab code may use: sequences, lyse routines, lab-local devices and
  plugins.

Each proposal is one of three:
- **Remove:** nothing outside the suite can reach it, or it can never work.
- **Ian's call:** public on `master`, so lab code could reach it, but nothing in
  the suite uses it. The proposal is to remove it if Ian agrees.
- **Keep:** user-facing, or still live. The figure in brackets is what removing
  it would save.

### Found while listing: step 3 entries 5 and 6 changed upstream plugin forms

Upstream blacs asks its plugins for `get_callbacks` and retries a no-argument
`plugin_setup_complete()`; since d515339 and 2cf4b3b neither works. Ian decided
that lab plugins written for upstream are unsupported (2026-10-11), and step 3
entries 5 and 6 now say so.

### 1. Demo blocks under `if __name__ == '__main__'` that nothing runs

- Where: blocks from the `if` line to the end of the file, 13 files:
  - `double_import_denier.py:171`, `filewatcher.py:240`, `modulewatcher.py:128`
    and `splash.py:134`;
  - `qtwidgets/`: `dragdroptab.py:853`, `elide_label.py:152`,
    `headerview_with_widgets.py:230`, `analogoutput.py:230`, `ddsoutput.py:117`,
    `digitaloutput.py:74`, `enumoutput.py:126`, `imageoutput.py:178` and
    `toolpalette.py:443`.
  - Also the commented-out block at `connections.py:354-361`.
  - Seven of the qtwidgets files import `sys` only for their block.
- Callers: none. pyproject's one entry point is `labscript-profile-create`. No
  doc or repo runs these files. Control: the same grep finds `zlock.py:37`,
  which `ls_zprocess.py:468` runs as `-m labscript_utils.zlock`.
- Public: no, being script tails. On `master`: yes. User code cannot reach them.
- Proposal: remove, with their `# A simple test!` comments and unused
  `import sys`. The widget demos are a developer's only visual harness.
- Core lines: 310.
- Owner edits: none.

### 2. `AnalogInput` and its `PlotWindow`

- Where: `qtwidgets/analoginput.py` (whole file), and
  `qtwidgets/InputPlotWindow.py` (whole file), which only it imports.
- Callers: none.
  - No file in any repo imports `analoginput`. The class is used only in its own
    demo.
  - blacs sets widgets with `set_AO`, `set_DO`, `set_EO` and `set_Image`;
    nothing calls `set_AI`.
  - The token count missed it because labscript's `docs/labscript-dev/main.tex`
    names an unrelated `AnalogInput`.
  - Control: `set_AO` hits blacs `output_classes.py:261, 289`.
- Public: yes. On `master`: yes. User code could reach it only through a
  lab-local BLACS tab that imports it by path.
- Proposal: Ian's call.
- Core lines: 176, the two files with banners.
- Owner edits: none.

### 3. The base `MenuContext.render`

- Where: `plugins.py:847-981`. The class docstring (814-821) and module
  docstring (56-59, 103-114, 345-371) describe it.
- Callers: none reach it.
  - hyde's `HydeMenuContext.render` (`shared/plugin.py:874`) overrides it and
    never calls `super().render()` (rc=1).
  - BLACS uses `MenuBuilder`.
  - Its seven tests went in 16a3589.
  - Control: `MenuContext` hits hyde `plugin.py:666` and `plugins.py:814`.
- Public: yes (`__all__`). On `master`: no.
- Proposal: remove, as Ian already decided. `MenuContext` keeps the
  registration that hyde uses. The module docstring loses about 39 lines.
- Core lines: 119.
- Owner edits: hyde rewords about 14 lines of docstrings and comments that name
  the base renderer (`plugin.py:495, 647-652, 887-889`).

### 4. `testing_utils`, which nothing imports

- Where: `testing_utils.py`, the whole file: `monkeypatch`, `Any` and `ANY`,
  `ThreadTestCase` with its debug prints, `dotdict` and `quit_mainloop`.
- Callers: none.
  - `testing_utils` matches only its own banner in any repo.
  - `monkeypatch` hits are pytest's fixture, and the `ANY` hits are licence text.
  - Control: `LabConfig` matches in 8 repos.
- Public: yes. On `master`: yes, unchanged. A lab-local test could import it.
- Proposal: Ian's call. If it stays, the two debug prints in `ThreadTestCase`
  (lines 84, 87) go anyway.
- Core lines: 119 with the banner, or 2 if it stays.
- Owner edits: none.

### 5. `ToolPaletteGroup`'s dead methods, and `ToolPalette.updateMinimumSize`

- Where: `qtwidgets/toolpalette.py`.
  - Stubs: `insert_new_palette` (102-106) and
    `remove_from_linked_width_group` (212-214) are `pass`. `remove` (139-143)
    checks the name and does nothing. `reorder_palette_by_index` (128-137)
    raises `NameError` on an undefined `count`.
  - Their forwarders: `reorder_palette` and `remove_by_index`.
  - Never called: the `*_by_index` methods (87-88, 99-100, 119-120) and the
    linked-width feature (161-243), that is `widths_linked`,
    `create_linked_width_group`, `add_to_linked_width_group` and
    `_create_find_max_function`.
  - Then unreferenced: `get_name_from_index` and `get_index_from_name`.
  - `updateMinimumSize` (380-381) is not a Qt virtual.
- Callers: none. BLACS uses only `has_palette`, `get_palette` and
  `append_new_palette` (`device_base_class.py:373-376`,
  `output_classes.py:957-960`). Control: `append_new_palette` hits blacs
  `device_base_class.py:376`.
- Public: yes. On `master`: yes. A lab tab building its own group could call
  one, but four of the methods cannot work.
- Proposal: Ian's call. `_find_max_item_width(name)` keeps its last branch,
  which `ToolPalette` calls at line 294.
- Core lines: 106.
- Owner edits: none.

### 6. `dragdroptab.debug`, a tracing switch that only a source edit turns on

- Where: `qtwidgets/dragdroptab.py:20-36` (the class) and 39-44 (its print
  block), plus 42 `@debug.trace` decorators.
- Callers: `DEBUG = False` is a class constant, so `trace` returns each function
  unchanged. Nothing sets it: only line 39 contains `debug.DEBUG`. Control:
  `dragdroptab` hits blacs's three `DragDropTabWidget` imports.
- Public: the name yes, but nothing uses it. On `master`: yes. User code cannot
  reach it.
- Proposal: remove. Behaviour is unchanged, since `trace` is the identity.
- Core lines: 65.
- Owner edits: none.

### 7. `ConnectionTable.assert_superset` and `Connection.diff`

- Where: `connections.py:84-124` and 280-281, and the `dict_diff` import (21),
  which only they use.
- Callers: none. Upstream's apps never called it either (rc=1 at `master` in
  blacs, runmanager, lyse, runviewer, labscript and labscript-devices). It does
  the check `compare_to` does, raising instead of returning. Control:
  `compare_to` hits blacs `front_panel_settings.py:78` and
  `shot_execution.py:364`.
- Public: yes. On `master`: yes. A lab script could call it.
- Proposal: Ian's call. The `dict_diff` module stays: runmanager and lyse import
  it.
- Core lines: 40.
- Owner edits: none.

### 8. runmanager's `get_shot_globals`, lyse's `get_check_state`, and three more shims in other repos

- runmanager `get_shot_globals` (`__init__.py:928-940`), a FutureWarning
  forwarder to `labscript_utils.shot_utils.get_shot_globals`.
  - Callers: none in the suite.
  - Public, and on `master`: lab lyse routines call
    `runmanager.get_shot_globals`, which is what the warning is for.
  - Keep (Ian's call) [12 lines, with its `warnings` and `shot_utils` imports].
- runmanager `from labscript_utils import dedent` (`__main__.py:76`): unused.
  Control: `master` uses it at 3712. Remove, 1 line.
- lyse `get_check_state` (`utils/gui.py:98-111`).
  - It is a PyQt5 shim in a PyQt6 suite. Its callers are `__main__.py:258` and
    `263`.
  - On `master`, but no routine has a reason to import `lyse.utils.gui`.
  - Remove: the two callers use `.checkState().value`. 12 lines.
- blacs `plugins.get_callbacks(name)` (`plugins/__init__.py:34-36`) forwards to
  `manager.get_event_handlers`.
  - Callers: `shot_execution.py:777, 935, 1032, 1147`. Its test,
    `tests/test_plugins_compat.py`, covers only it and module loading.
  - Remove: the callers use `plugins.manager.get_event_handlers`. 3 lines, plus
    the 61-line test file.
- blacs `execute_program` (`__main__.py:691-694`) wraps `qapplication.exec()`
  and drops its exit code. Remove: `sys.exit(qapplication.exec())`, 2 lines.
- Controls: each definition, and `compare_to` above.
- Core lines: 18, or 30 with `get_shot_globals`.
- Owner edits: runmanager (`__main__.py:76`); lyse (`utils/gui.py`,
  `__main__.py:258, 263`); blacs (`plugins/__init__.py`, the four
  `shot_execution.py` calls, the test file, `__main__.py:691-694`).

### 9. `TubingenCameraServer`

- Where: `camera_server.py:140-188`.
- Callers: none. The header (26-31) points to it as the worked example.
- Public: yes. On `master`: yes. Lab camera servers copy it rather than import
  it.
- Proposal: keep, since it is the documented example (Ian's call). Removing it
  takes the header sentence and three imports with it.
- Core lines: 0 [46].
- Owner edits: none.

### 10. The `ls_zprocess` forwarders

- Where: `ls_zprocess.py`:
  - `Event` (364-365) and `Handler` (368-369);
  - eight `zmq_get*` and `zmq_push*` (372-401);
  - `RemoteProcessClient` (404-408).
  - `Lock` is not one: it drops `read_only` for an old zlock server.
- Callers:
  - `zmq_push_multipart`: runmanager `__init__.py:37, 884, 922`.
  - `Event`: blacs `plugins/progress_bar/__init__.py:33, 65`.
  - `Handler`: `setup_logging.py:17, 52`.
  - `RemoteProcessClient`: blacs `tab_base_classes.py:36, 337`.
  - The other seven have no caller. labscript-devices' `Camera.py` calls plain
    `zprocess.zmq_get_string`, not this one.
  - Control: the runmanager call.
- Public: yes. On `master`: yes. Lab device code may call `zmq_get` and the
  rest.
- Proposal: keep, since they are user-facing (Ian's call). If they go:
  - callers move to `ProcessTree.instance().event`, `.logging_handler` and
    `.remote_process_client`, and to `ZMQClient.instance().push_multipart`;
  - `RemoteProcessClient` loses its labconfig default port.
- Core lines: 0 [25].
- Owner edits, only if they go: runmanager (3 lines), blacs (4), labscript-utils
  `setup_logging` (2).

### 11. `import_or_reload` and `labscript_utils_dir`

- Where: `__init__.py:38-49` and 34-35.
- Callers: none.
- Public: yes. On `master`: yes. Lab experiment code imports both from
  `labscript_utils`.
- Proposal: keep, since they are user-facing (Ian's call).
- Core lines: 0 [14].
- Owner edits: none.

### 12. `BasePlugin.get_menu_class`

- Where: `plugins.py:709-720`. Its default returns None, and its docstring says
  it is deprecated.
- Callers:
  - `PluginManager.setup_plugins` calls it on every plugin (line 1109).
  - All seven blacs plugins define their own. hyde never calls `setup_plugins`.
  - Tests: `test_plugins.py:43` asserts the default, and the test at 157-186
    inherits it.
  - Control: blacs's seven definitions.
- Public: yes. On `master`: no, since `BasePlugin` is the fork's.
- Proposal: remove. The `BasePlugin` docstring lists the hook among those a
  BLACS plugin defines. The 157-186 test defines its own.
- Core lines: 10, minus 1 test line and plus 2.
- Owner edits: none.

### 13. `double_import_denier.disable`, `TomlConfigParser.to_toml_dict` and `write_toml`

- `disable` (`double_import_denier.py:160-168`) undoes `enable()`.
  - Callers: none. `labscript_utils/__init__.py:100` and `h5_lock.py:21-23` use
    `enable()` and `_denier`.
  - Public, and on `master`: Ian's call, 9 lines.
- `to_toml_dict` and `write_toml` (`labscript_profile/toml_config.py:152-161`).
  - Callers: none. hyde's `write_toml` is its own function.
  - Not on `master`. Remove, 9 lines.
  - `dump_toml_file` stays, with its three callers.
- Controls: `enable` hits `__init__.py:100`; `read_toml` hits
  `labscript_profile/__init__.py:70`.
- Core lines: 9, or 18 with `disable`.
- Owner edits: none.

### 14. The output widgets' `get_AO`, `get_DO`, `get_EO` and `get_Image`

- Where: `analogoutput.py:162-163`, `digitaloutput.py:42-43`,
  `enumoutput.py:79-80` and `imageoutput.py:147-148`.
- Callers: none. Their `set_` pairs are blacs's.
- Public: yes. On `master`: yes. They are how a lab-local tab reads a widget's
  output.
- Proposal: keep, since they are user-facing (Ian's call).
- Core lines: 0 [8].
- Owner edits: none.

### 15. `ShotQueueWidget._update_button_states` and `FILEPATH_COLUMN`

- Where: `qtwidgets/shotqueue.py:210-211`, a `pass` stub called at 118.
  `FILEPATH_COLUMN` is at 21, in `__all__` at 31, and the default of
  `path_column` at 90.
- Callers:
  - The stub: its one call. runmanager's subclass does not override it.
  - `FILEPATH_COLUMN`: both callers pass `path_column` (runmanager
    `queueing.py:159`, `tests/test_shotqueue.py:22`). blacs's two constants of
    that name are its own.
  - Control: `path_column` hits runmanager.
- Public: `FILEPATH_COLUMN` yes. On `master`: no, since `shotqueue.py` is the
  fork's.
- Proposal: remove both. `path_column` becomes a required keyword.
- Core lines: 5.
- Owner edits: none.

### 16. Small private leftovers in labscript-utils

- `COMMUNICATION_DEFAULT_TIMEOUT` (`ls_zprocess.py:235-237`): used once, as a
  fallback at 288, and imported nowhere. Not on `master`. Inline `60`: 3 lines.
- `configure_qapplication`'s non-darwin early return (`splash.py:43-44, 52-53`).
  On other platforms nothing reads the property it sets, so the guard moves
  into the darwin branch: 3 lines.
- `_resolve_appconfig_save_path` (`labconfig.py:245-246`). Its two callers call
  `appconfig_path_with_suffix(filename, '.toml')`: 2 lines.
  - It is not the load resolver's twin: that one still finds a legacy `.ini`.
- `TomlConfigParser.read_toml`'s first `isinstance(data, dict)`
  (`toml_config.py:140-141`): `tomllib` always returns a dict, which was shown
  on four inputs. 2 lines.
- `initial_size` (`dragdroptab.py:168`): assigned, never read. 1 line.
- `get_default_appconfig_file`'s `except (NoOptionError, NoSectionError)`
  (`labconfig.py:58`).
  - The `default` section never raises `NoSectionError`, shown by running
    LabConfig on a file without one. The control, a missing section, raises it.
  - Edit to `except LabConfig.NoOptionError:`, 0 lines.
- `ElideScrollArea`'s `self.widget is None or` (`elide_label.py:36, 43`):
  `widget` is a method, so the test is never true. Edit, 0 lines.
- Controls: each name's own uses in the file.
- Public: only the first, which is not on `master`. User code cannot reach any.
- Proposal: remove or edit all.
- Core lines: 11.
- Owner edits: none.

### 17. Public leftovers with no caller: `add_folder`, `remove_callback`, `icon_frac`

- `FileWatcher.add_folder` (`filewatcher.py:205-206`): `add_folders` and
  `add_file` stay in use. 2 lines.
- `Settings.remove_callback` (`settings.py:143-144`): its pair
  `register_callback` is used at blacs `__main__.py:346`. 2 lines.
- `Splash.icon_frac` (`splash.py:79`): nothing reads it, so a subclass setting
  it has no effect either. 1 line.
- Callers: none. On `master`: yes, but these are BLACS, lyse and splash
  internals that user code has no reason to reach.
- Proposal: remove.
- Core lines: 5.
- Owner edits: none.

### 18. `__main__` blocks that only a developer runs

- Where: `impprof.py:59` (3 lines), `shared_drive.py:38` (6) and
  `versions.py:302` (6). The last two are assert-only self-checks that pytest
  does not run.
- Callers: none in any repo.
- Public: run as `python -m`. On `master`: yes.
- Proposal: Ian's call. The two self-checks would belong in `tests/` by rule 13.
- Core lines: 15.
- Owner edits: none.

### 19. `FileWatcher.get_modified_times` and its `modified_times` keyword

- Where: `filewatcher.py:201-203`, commented "Backward compat for BLACS from
  before file hashes", and 62-64.
- Callers: none, at `CodeHealth` or `master`. BLACS uses `get_modified_info`.
  Control: `get_modified_info` hits blacs `connection_table/__init__.py:245`.
- Public: yes. On `master`: yes.
- Proposal: keep, since it is user-facing (Ian's call).
- Core lines: 0 [6].
- Owner edits: none.

### 20. Kept by default: guards that need a test or still hold

- dragdroptab's PyQt4 workaround (`dragdroptab.py:555-561`): it runs on every
  tab drag. Whether Qt6 still needs it takes a manual drag test, so keep
  [6].
- `headerview_with_widgets.do_update_widget_positions`'s `except KeyError:
  return` (175-178).
  - It fires when a header widget is set before the model is attached, and the
    event loop runs before the header is shown.
  - lyse never does that, but a lab widget could, so keep [3].
- `memprof.check`'s `return True` (`memprof.py:57`). blacs connects it to a menu
  action, which drops the return value. Ian's call [1].
- `UnitConversion.unit_list` (`UnitConversionBase.py:53`), commented as an alias
  for backward compatibility. A lab unit conversion may read it, so keep [1].
- `excepthook.l`, a namespace class: it holds the live logger (4 code lines and
  3 test lines). Keep, 0.
- `__main__` blocks that code or users run, kept, 0:
  - zlock and zlog, run by `ls_zprocess.py:468`;
  - remote, documented;
  - `tk_exception`, run by `excepthook`;
  - the profile's connection-table template;
  - `camera_server`, the documented way to run a server.

### 21. Already gone

- `get_callbacks` in labscript-utils, by d515339. Only prose names it.
- `Connection._deserialise`'s no-op comparison, by d784002.
- `EnumOutput.eventFilter`, `EnumOutput._lock_action` and the commented-out
  `ImageView.eventFilter`, all by f76d464. `_lock_action` lives on in
  `analogoutput.py`.
- The tuple unwraps after file dialogs: by d90310a, and in the owners' repos by
  9877b45, 20aabd4, 7e96ae4 and 4db574e.
  - Two adjacent one-line leftovers remain for their owners: blacs
    `connection_table/__init__.py:432` normalises an already absolute path, and
    runviewer `__main__.py:755` calls `str()` on a str.

### Outcome

Ian approved the round through the coordinator. Every commit is on CodeHealth;
none is merged or pushed.
- Removed in labscript-utils:
  - 1, 0b80481; 2, 194085f; 4, 36b41f7;
  - 5, cec879a, after which `ToolPalette` finds its own widest item;
  - 6, 1c09e6e; 7, 3e86ffa; 12, 8ae5a82; 13, b334ca7, `disable` included;
  - 15, e59d208; 16, 64e7a27; 17, 1f804ce;
  - 18, 03c6f09: the versions self-check is now `tests/test_versions.py`.
    shared_drive's was not moved, because the module reads the machine's
    labconfig at import, so a test would need a faked one.
  - 9, c9ab56f: `camera_server.py` is deleted. Ian: his labs do not use it, and
    a user who wants the classes can copy them into their own user devices.
    labscript-devices removed its legacy `Camera` and `PythonCamera` in
    e3203a9.
  - Review fix, 582e2f7: the palette order index and `ToolPalette`'s group and
    name, unused once the linked widths went.
- Entry 8 in the owners' repos:
  - runmanager ee9d787, the `dedent` import;
  - lyse f4c8e8e, `get_check_state`;
  - blacs ade39c6: the `get_callbacks` forwarder, `test_plugins_compat.py` and
    `execute_program`.
  - runmanager 9f44e2e and runviewer e36aaf9 drop their fixtures' citations of
    the deleted test. The meta repo's `IDIOMS.md:137` cites it too; that is the
    coordinator's to fix.
  - `get_shot_globals` stays.
- Held: entry 3, the base `MenuContext.render`. It waits for an evaluation of
  the plugin framework for blacs, which would need a renderer if it adopts
  `get_menu_contributions`.
- Kept as proposed: 10, 11, 14, 19 and 20, `memprof`'s `return True` included.
- Non-blank lines, code then tests: labscript-utils -1073 and +24; blacs -5 and
  -61; lyse -12 and 0; runmanager -1 and -2. In all, 1091 fewer code lines and
  39 fewer test lines.
- Every consumer's suite passes on its CodeHealth against labscript-utils 03c6f09:
  - runmanager 139, blacs 68, lyse 44, labscript-devices 41;
  - labscript-optimization 216, labscript-agents 15, runviewer 10, labscript 3;
  - hyde's 17 plugin-related test files.
  - After 582e2f7, labscript-utils passes 25 and blacs 68.

### Totals

21 entries.
- **Remove: 552 core lines, and a 61-line test file.**
  - labscript-utils: 534. That is 1 demo blocks (310), 3, 6, 12, 13's TOML pair,
    15, 16 and 17.
  - Other repos: 18, from entry 8's four shims (blacs 5, lyse 12, runmanager 1).
- **Ian's call: 466.**
  - 2 `AnalogInput` (176), 4 `testing_utils` (119), 5 `ToolPaletteGroup` (106),
    7 `assert_superset` (40), 13's `disable` (9), 18's `__main__` blocks (15),
    and `memprof`'s `return True` (1).
- **Keep: 121 in brackets.**
  - `TubingenCameraServer` 46, the `ls_zprocess` forwarders 25,
    `get_shot_globals` 12, `import_or_reload` and `labscript_utils_dir` 14;
  - the `get_` widget methods 8, `get_modified_times` 6, the PyQt4 workaround
    6, the headerview guard 3, and `unit_list` 1.
- Entry 3 is already decided.
- Owners who would make a change:
  - runmanager: entry 8's import.
  - lyse: `get_check_state`.
  - blacs: `get_callbacks` and `execute_program`.
  - hyde: entry 3's docstrings.
  - If the forwarders went: runmanager, blacs and labscript-utils.

### Seen for later steps

- `double_import_denier.py:20` has its own never-set `DEBUG = False`, read at
  59 and 66. Not checked here.
- blacs's "Reset profiler" menu item connects `memprof.start` to `triggered`,
  which may pass `checked` as its `filepath`. Not run; that is for blacs.
- blacs is the only app that does not use `exec_qapplication`, so it has no
  Ctrl-C timer. That is for blacs.
- Stale text in this file: the step 2 and 3 notes say the seven base-render
  tests and the aliases "go at step 4". Both have already gone.
- `versions.get_version` looks for a directory named after the module, so an
  installed single-file module (`subprocess`, `six`) comes back `NotFound`, and
  `check_version` would call it missing. The old self-check asserted
  otherwise and would have failed, on `master` too.
- `pyqtgraph` is in labscript-utils' dependencies, but no labscript-utils code
  imports it now. labscript-devices' `TriggerableCamera` imports it and declares
  only labscript-utils, so the dependency stays until that is settled.
- Unused imports that predate this step: `QtGui` in `elide_label.py` and
  `labscript_utils` in `settings.py`. Step 6.

## Step 5: spent documents

"A repo keeps its README, NEWS, AGENTS.md, docs/, and findings of bugs that were
found but not fixed. Any other plan, issue list or observation file goes when
spent. Intent documents state the current design only."

How the candidates were found:
- plugins.py's module docstring, section by section against the code;
- every docstring and comment in `labscript_utils` and `labscript_profile`;
- labscript-utils' non-code files;
- documents elsewhere that describe labscript-utils: other repos' docs, the
  meta repo's `issues/*.md`, `CODEX.md` and other top-level files, and
  labscript-library.

How they were checked:
- Refs: labscript-utils `CodeHealth` at 2fcd689, where every line number below
  points; other repos at `CodeHealth`; the meta repo and labscript-library at
  `HEAD`.
- A text is wrong if it names a name that is gone, shown by a `git grep` with
  exit 1 beside a control that matches, or if it contradicts the code at a
  given line.
- The "On merge" items are left to the merge.

Two facts frame the list:
- The INI-to-TOML conversion stays. Ian kept step 1 entries 1, 3 and 8: many
  labs still have INI files. So text describing the conversion is right, and
  text promising its removal is wrong (entry 14).
- No docstring, comment or non-code file in labscript-utils still names
  anything steps 2 to 4 removed.

### 1. plugins.py's module docstring, 608 lines

- What: `plugins.py:14-621`, longer than the code it documents (622-1300).
- Why: little is wrong, and almost all of it duplicates or teaches.
  - Duplicates: `Callback` and `callback` (45-49), the settings, legacy-menu,
    notification and event-priority skeletons (289-344, 524-571), and `close()`
    (608-621). Each repeats a class or method docstring.
  - Tutorials: a whole-application example (67-145) and a whole-plugin example
    (146-267).
    - The application example combines BLACS's `setup_plugins` path with hyde's
      contexts path, which no application does together.
    - Both real applications are better examples.
  - Wrong:
    - 453-454 name `create_tabs()` and `create_mdi_windows()`, which exist
      nowhere now;
    - 16-19 say "callbacks";
    - 56 says the contribution path is "for future applications", though hyde
      runs it.
  - The setup-activity contract (572-607) and the configuration rules (36-44)
    live only here: `setup_complete` and `discover_modules` have one-line
    docstrings.
- Held, verbatim: the `MenuContext` bullet (56-59) and the contribution-menu
  skeleton (345-445), for the evaluation of the plugin framework at blacs's
  pass. The same goes for the application's `MenuContext` calls (103-107,
  113-114), 9 lines, if the hold is read broadly.
- Proposal: keep 34 lines plus the held 114:
  - purpose and ownership;
  - the package layout and the `Plugin(initial_settings)` contract;
  - the two menu paths, with MenuBuilder's in 3 lines;
  - the UI-context paragraph.
  - Delete the rest.
  - The facts found only here move, as 42 lines, into the docstrings of
    `PluginManager` (the call order), `discover_modules` (the configuration
    rules and the `ValueError`), `setup_plugins`, `MenuBuilder`,
    `register_context`, `setup_contexts` and `setup_complete`. Drafts are in the
    scratch report.
- For the evaluation:
  - flagged: the two-menu-paths framing, the UI-context paragraph, both
    examples, the UI-homing section (447-523) and the setup activities. The
    service design is documented only at `BasePlugin.get_services` and
    `collect_services`.
  - in the held skeleton: groups sort by name with ungrouped first, so its
    `Quit` (group `application`) draws first. It was shown by running.
- Lines: -460 in the docstring, +42 elsewhere, net -418.
- Owner: labscript-utils.


### 2. The meta repo's `labscript_project.md`, an orientation snapshot

- What: `labscript_project.md`, 330 lines. It is untracked: the meta repo's
  `.gitignore` ignores it.
- Why wrong: it names code that is gone or renamed:
  - `__version__.py` (42), `camera_server.py` (53, 104, 251), and
    `testing_utils.py` with `unitconversions/test.py` as the only tests
    (114-116; `tests/` now holds eight files);
  - `blacs/experiment_queue.py` (126), `connections._ensure_str` (192) and
    `Camera.py` (240).
  - It has misled agents before. capabilities.md and the inventories do the same
    job.
- Proposal: delete. Being untracked, it cannot be got back through git. If kept,
  correct the lines named.
- Lines: -330, outside any diff.
- Owner: coordinator.


### 3. labscript-suite's `RunmanagerQueue.md`, a finished plan

- What: `RunmanagerQueue.md`, 215 lines, on labscript-suite `CodeHealth`.
- Why spent:
  - It is a worker plan for work merged in every Development (`CODEX.md:65`),
    ending in "Implemented Follow-Ups".
  - Some widget features it plans went in step 1 (b857f3e).
  - Its `BLACS['experiment_queue']` alias (131) is gone.
- Proposal: delete.
- Lines: -215.
- Owner: labscript-suite, edited by the coordinator.


### 4. `issues/server_interfaces_2026_09_25.md`: process, steps and status, and three names

- What: Process (125-136), Steps (148-194) and Status (206-232); and lines 5,
  63-64 and 152-153.
- Why:
  - `CODEX.md:55` records ServerInterfaces merged and pushed in all six repos, so
    "nothing is pushed" (208) is false. The rest is completed work.
  - `CameraServer` (5, 152-153) is gone.
  - `COMMUNICATION_DEFAULT_TIMEOUT` (63-64) is now an inline 60 (64e7a27).
- Proposal: delete the three sections. Line 5 names TriggerableCamera's
  `ImageReceiver`; 63-64 say "fallback 60".
- Lines: -87.
- Owner: coordinator.


### 5. Smaller comment and docstring corrections in labscript-utils

- Overlong comments shortened to three lines saying why:
  - `modulewatcher.py:69-73, 112-116, 122-125`;
  - `double_import_denier.py:127-132`, whose 98, 100 and 105 restate the code;
  - `dragdroptab.py:294-301`, and 497-499, which also names PyQt4;
  - `setup_logging.py:46-50`, and 33-35, which narrates;
  - `ls_zprocess.py:341-344`. The same file's 170-172 is a spent Python 3 note,
    and its 333 restates the code. Its 173-175 error message names the
    `labscript_utils.zprocess` module, which does not exist, and `ZMQserver`.
- History, or a dead link:
  - `excepthook/__init__.py:40-44`, a SourceForge tracker link, and 100-104,
    written in the first person;
  - `toml_config.py:8-15`, "as it always did under INI".
- Wrong:
  - `labscript_profile/__init__.py:18-25`: the `.pth` runs one function, not
    two.
  - `filewatcher.py:136` sits above the wrong branch.
  - `create.py:142` names `appratus_name`.
  - `analogoutput.py:150, 158` and `enumoutput.py:64, 75` name the wrong
    widget.
  - The profile's two IMAQdx examples (line 27) say `python - m`.
- Overlong docstrings: `appconfig_path_with_suffix` (`labconfig.py:219-226`) and
  `unescape_braces` (`lookup_format.py:35-42`). The latter explains
  runmanager's internals.
- Comments that guard code with no remaining use:
  - `unitconversions/__init__.py:48-53`, for a BLACS that read full names;
  - `device_registry/__init__.py:3-7`, for labscript-devices older than 3.1.
    labscript-suite requires 3.3.
  - `headerview_with_widgets.py:86, 180`, for QVariant API 1, which PyQt6 never
    returns.
  - Ian's call: their code, 21 lines, would go too. That is step 4 matter.
- Restating: `create.py:94, 96, 98, 119, 172`; `connections.py:98, 208, 271`.
- Proposal: as each says; the replacement texts are in the scratch report.
- Lines: -71.
- Owner: labscript-utils.


### 6. `toolpalette.py`: commented-out code and a 17-line comment

- What: 23 lines of commented-out code, among them Python 2 prints, and the
  `resizeEvent` comment (259-275).
- Proposal: delete the 23. Shorten the comment to three lines: a column change
  adds or removes a scrollbar, which triggers another `resizeEvent`, so the
  layout is skipped until a posted event re-enables it.
- Lines: -37.
- Owner: labscript-utils.


### 7. `versions.py`'s docstrings

- What: `_get_metadata_version` (82-97) and `_get_literal_version` (114-122),
  which are internal; and the opening paragraphs of `get_version` (179-187) and
  `check_version` (250-260).
- Why: overlong. `get_version`'s paragraph also omits the setuptools_scm lookup
  that the code tries first (225).
- Proposal:
  - one line for each internal docstring;
  - four lines for `get_version`, naming its lookups in order;
  - five lines for `check_version`.
  - `Args` and `Raises` stay.
- Lines: -33.
- Owner: labscript-utils.


### 8. labscript-library: notes for gone names, two capabilities, and a stale inventory

- What:
  - 26 notes name code that no longer exists, each one reported by the
    generator: 19 in `notes/labscript-utils.txt`, 2 in `blacs.txt` and 5 in
    `labscript-devices.txt`.
  - `notes/labscript-utils.txt:54` says the first service registration wins,
    but `collect_services` raises on a duplicate (cf70352).
  - `capabilities.md:59` names the deleted `fingertab`.
  - `capabilities.md:62` says `ShotQueueWidget` edits shot files with drops and
    delete. It now shows rows built from row-info dicts, with selection by id
    (b857f3e).
- The inventory is generated at labscript-utils e04a8ef, 31 commits behind.
  Regenerate it; do not edit it.
- Proposal: delete the 26 notes, correct 54, delete 59 and correct 62. Then
  regenerate at the merge.
- Lines: -27 by hand.
- Owner: librarian.


### 9. `issues/plugin_refactor_prd.md`: deprecated hooks and warnings that went

- What: 36-37, 45-50, 59-61, 81-82, 92-96, 117-121, 127 and 140-148.
- Why:
  - `PluginManager` asks only for `get_event_handlers` and warns of nothing
    (d515339).
  - `BasePlugin` keeps five methods, not the hooks the text lists (59-61).
  - Plugins written for upstream are unsupported, by Ian's decision.
  - blacs's plugins are moved (127; dee664a).
  - The Status (45-49) and Further Notes (140-148) sections are history.
- Proposal: delete the spent stories and sections. Lines 81-82 become one line
  saying only `get_event_handlers` is asked. Lines 59-61 list the five methods.
- Lines: -27.
- Owner: coordinator.


### 10. `device_registry/_device_registry.py`: a 35-line string about "old" and "new" methods

- What: 12-46, a bare string after the imports, so not a docstring; and 161-164,
  "will be deprecated in the future".
- Why: overlong, and it narrates a transition. Both lookup paths still work as
  described.
- Proposal: about 11 lines stating the two mechanisms as they are, and a
  one-line comment at 161.
- Lines: -26.
- Owner: labscript-utils.


### 11. `issues/seen_while_mapping.md`: entries dealt with

- labscript-utils sections: lines 8-13, 15, 18, 38, 39, 42-44, 47 and 48 are
  done.
  - The demo blocks, `debug`, `camera_server`, `unitconversions.test` and the
    output-widget copies are gone, and so are `assert_superset`, the zprocess
    helpers, the `widget is None` test and `testing_utils`.
  - `_deserialise` is gone, `ensure_str` is shared, and the forwarders and
    `excepthook.l` were kept by decision.
  - Line 41 keeps only the PyQt4 workaround.
- Other repos' entries that name removed labscript-utils code: 30, 31, 241-244,
  270, 274 and 283-284 can go. Lines 85, 154, 157, 247, 268 and 276 each drop a
  clause.
- The file itself says each pass deletes what it deals with. Lines 14, 21 and 40
  are on the merge list.
- Lines: -25, and 7 changed.
- Owner: coordinator.


### 12. Docs boilerplate shared by eight repos

- What, identical in labscript-utils, runmanager, blacs, lyse, runviewer,
  labscript, labscript-devices and labscript-suite:
  - an SVG logo that nothing references (579 lines);
  - the to-do machinery with no `.. todo::` anywhere: `index.rst:1-4, 37-38`,
    and `conf.py`'s `sphinx.ext.todo` and `todo_include_todos` (18 lines);
  - `conf.py`'s `qt` intersphinx mapping to PyQt5, with a 64 KB PyQt 5.11.1
    inventory file and a stale pyqtgraph comment (6 lines). No cross-reference
    uses it, and the suite is PyQt6.
- Evidence: the SVG's name matches nothing outside itself in any of the eight
  repos (exit 1); the control, `labscript_64x64`, matches `conf.py:32`.
- Proposal: delete all three, once and for all eight. `conf.py:35` calls its
  general section identical across projects.
- Lines in labscript-utils: -24 text lines, plus the SVG and the inventory.
- Owners: each of the eight repos, the same edit.


### 13. `settings.py` and the unit conversions' copied comments

- `settings.py`: 104, 106 and 113-119 are a commented-out `gtk.Image` block, and
  35-38 speculate. Delete them, and shorten 35-38 to two lines. -11.
- `aom.py`, `linear_coil_driver.py` and `optotunelens.py`:
  - "loaded from a globals.h5 type file" is wrong: the parameters come from the
    connection table (`properties.py:120-123`).
  - The formula comments name parameters that `aom` and `optotunelens` do not
    have.
  - "We should probably also store some hardware limits" is speculation.
  - Delete them, and correct optotunelens' formula. -11.
- Lines: -22.
- Owner: labscript-utils.


### 14. Text that promises the INI conversion's removal

- What:
  - "LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED." 12 times, in
    `labscript_profile/__init__.py`, `create.py`, `labconfig.py` and
    `qtwidgets/application.py`;
  - "Temporary ... Slated for removal soon" in six docstrings
    (`labscript_profile/__init__.py:52, 83, 147`, `labconfig.py:194, 265, 292`);
  - `labconfig.py:214`.
- Why wrong: Ian kept the conversion (step 1, entry 1). The code still runs it
  (`labscript_profile/__init__.py:88-95`, `labconfig.py:238-241, 297-313`).
- Proposal: delete the markers, and reword the docstrings to say what they do.
  `labconfig.py:205` is user-facing, so it is Ian's call: a FutureWarning that
  says INI support is slated for removal.
- Lines: -20.
- Owner: labscript-utils.


### 15. `unitconversions/example.py`: one teaching comment three times

- What: the same 5-line comment at 19-23, 57-61 and 86-90, and 54 and 83.
  "#here is the calibration code" appears at eight places.
- Proposal: keep the comment once, in `example1`, as three lines; delete the
  repeats and six of the eight calibration lines.
- Lines: -20.
- Owner: labscript-utils.


### 16. Commented-out code in five qtwidgets files

- What: `imageoutput.py:34, 118, 159`; `analogoutput.py:130, 131, 141`;
  `ddsoutput.py:45, 83, 85`; `enumoutput.py:98, 101`; and `elide_label.py:73`
  with 98-101, a commented-out `resizeEvent`.
- Proposal: delete.
- Lines: -16.
- Owner: labscript-utils.


### 17. plugins.py's class docstrings and comments

- What:
  - `PluginManager`'s docstring (974-978) says it keeps two mappings, but it
    keeps four (1013-1016).
  - `BasePlugin.get_event_handlers` says the manager "normalizes" handlers,
    which it no longer does (1269-1272).
  - `BasePlugin.get_services` names `plugin_setup_complete()` where it means
    `setup_complete()`.
  - `render` has a 5-line comment (956-960), which is held with `render`.
  - Eight label comments in `setup_plugins` restate the next line.
  - `setup_plugins` calls its menu and notification hosts "legacy".
- Proposal: delete 974-978, drop "normalizes", correct the name, delete the
  labels and drop "legacy". Shorten 956-960 when the hold lifts.
- Lines: -16.
- Owner: labscript-utils.


### 18. `shotqueue.py` and `link_indicator.py`

- `shotqueue.py:21-25, 44-49, 149-154`: three good reasons, told at length. Cut
  each to three lines: -8.
- `LinkIndicator`'s docstring (28-65, 38 lines):
  - Lines 30-35 describe layout the code shows.
  - The Examples section repeats the constructor.
  - Shorten 30-35 to four lines and drop the examples: -8.
- Lines: -16.
- Owner: labscript-utils.


### 19. `h5_lock.py`: a 16-line comment with a promise

- What: 68-83: "I will report this as an issue in h5py, and will remove this
  workaround if it is fixed".
- Proposal: three lines saying why the workaround avoids the deadlock.
- Lines: -13.
- Owner: labscript-utils.


### 20. `CODEX.md`'s entries about labscript-utils

- `CODEX.md:335-341` is a note about `fingertab.py`, deleted in a885dec.
  Delete it: -7.
- The PluginRefactor section (947-950, 976-977, 988-990):
  - BLACS's events now come only from `get_event_handlers`, and its plugins are
    moved.
  - It also cites `plugin_extraction_proposal.md`, which no repo ever held.
  - Correct both, and drop the citation: -2.
- 327-329: the shot queue's method counts are out of date, at six defined and
  about ten inherited. Correct them.
- The `UpstreamBugFixes` row (66) omits labscript-utils' 635aea9, e08fbe6 and
  086a267; the last two are unpushed. Add a sentence.
- Also, in the meta repo:
  - `issues/code_quality_review_2026_10_07.md` item 15 lacks the new floors
    (package_version, the new modules, setuptools_scm>=10), +1;
  - its item 18 example now holds only for excepthook;
  - `code_health_campaign.md:125`'s "grown by 40%" is now about 18%.
- Lines: -8.
- Owner: coordinator.


### 21. `README.md`'s upgrade note

- What: `README.md:22-27` repeats the `tomli-w` note in `NEWS.md:3-5`.
- Why: a fresh install gets the dependency (`pyproject.toml:42`). The note
  serves old environments, which NEWS already addresses. NEWS keeps it, because
  `labscript-suite.pth` swallows the `ModuleNotFoundError`.
- Proposal: delete it from the README.
- Lines: -6.
- Owner: labscript-utils.


### 22. One-line corrections in labscript-utils' documents

- `example.toml:28`: `zlog = 7340` is read by nothing, since `ls_zprocess.py:91-94`
  hard-codes the port. Delete it.
- `labconfig.rst:2`: the title underline is one character short, since the
  fork's `.toml` edit, and Sphinx warns on every build. Lengthen it.
- `AGENTS.md:3` says every other suite repo imports labscript-utils. zprocess,
  desktop-app and labscript-c-extensions do not; say "nearly every".
- `NEWS.md:70`: the link to PR #92 goes to 88, as it does on `master`. Correct
  it.
- Lines: -1, and 3 changed.
- Owner: labscript-utils.


### 23. labscript-devices' `user_devices.rst:16`

- What: it names the labconfig `labconfig.ini`. It is `<host>.toml`.
- Proposal: "in the labconfig file".
- Lines: 1 changed.
- Owner: labscript-devices.

### Outcome

Ian decided through the coordinator, and in this session for the Qt links. Every
commit is on CodeHealth; none is merged or pushed.
- labscript-utils, 15e4b08..61df8f4: every entry as proposed, with these changes.
  - 1: the held parts are unchanged. The excerpt keeps the lines the proposal
    chose, so the `mdi` and `dialogs` registrations went with their contexts.
  - 5: the labscript-devices<3.1 block and headerview's QVariant API 1 branches
    went with their comments. The unitconversions full-name globals stay,
    marked due for removal (Ian).
  - 14: the "will be removed" notes stay, since Ian means to drop the conversion
    one day. Only "soon" went, and the FutureWarning is unchanged.
  - 17: `render`'s comment is held with `render`.
  - 61df8f4, review fixes: four docstrings made exact, and the device registry's
    text made its module docstring.
- Entry 12, corrected:
  - The unused SVG was in labscript-utils and labscript only.
  - labscript-suite keeps its to-do machinery, since it has real to-dos.
  - The PyQt5 inventory was not unused: it linked the Qt type names in inherited
    methods' signatures. Ian chose PyQt6 links instead. adf3168 adds
    `pyqt6-modified-objects.inv` (89 KB): PyQt6's classes and enums with short
    aliases, built from Riverbank's `objects.inv` after msl-qt's script.
  - Nitpicky builds now resolve more than with PyQt5: runmanager 4632
    unresolved against 4646, and labscript-utils 9314 against 9336.
- Owners:
  - runmanager 16857fd, blacs a193f2e, lyse 3a0dff4, runviewer fa6b8d5,
    labscript e7a5e4d;
  - labscript-devices f4e6d4f, with `user_devices.rst`;
  - labscript-suite 45eb515, by the coordinator, with `RunmanagerQueue.md`
    deleted.
  - The coordinator makes the meta-repo edits. It leaves
    `plugin_refactor_prd.md` untouched (Ian), and handles `labscript_project.md`,
    whose coupling notes go to the librarian.
  - librarian 1691f7d: the 26 notes, the services note and two capabilities.
    The inventories are regenerated.
- Lines in labscript-utils: Python files +183 and -905, net -722; other text -14
  net; and the SVG, -579.
- Tests: labscript-utils passes 25 at 61df8f4. Every consumer's suite passes on
  its CodeHealth against labscript-utils adf3168:
  - runmanager 139. One run hung while runmanager's own session ran its suite at
    the same time, and was stopped; the rerun took 11 s.
  - blacs 68, lyse 44, labscript-devices 41;
  - labscript-optimization 216, labscript-agents 15, runviewer 10, labscript 3;
  - hyde's 17 plugin-related test files.

### Totals

23 entries.
- labscript-utils: 739 lines.
  - plugins.py's module docstring, net -418;
  - other docstrings and comments, -290;
  - documents, -31, of which -24 is boilerplate.
  - Also the shared SVG (579 lines) and the PyQt5 inventory.
  - 21 lines of compatibility code are Ian's call.
- Coordinator: -147 in the meta repo, -215 for labscript-suite, and the
  untracked `labscript_project.md`, -330.
- librarian: -27, then a regenerated inventory.
- labscript-devices: 1 line changed.
- The seven other docs trees: the same boilerplate edit as entry 12.
- In all, 1128 hand-edited lines in tracked files.
- Held: 114 lines of plugins.py's docstring, until the evaluation at blacs's
  pass.
- Ian's calls:
  - the 21 code lines in entry 5;
  - the FutureWarning text in entry 14;
  - entry 12, as it spans eight repos;
  - deleting the untracked `labscript_project.md`.

## Step 6: style

"Whole-file passes under labscript-style." For this step, the skill's "old code
keeps its old forms unless the work touches them" does not apply: the pass is
the work.

How it was done:
- Seven Sonnet workers, each with the skill and a shared brief, covered every
  `labscript_utils` and `labscript_profile` module, 62 in all.
- Each worked in its own detached worktree of a273bf1. Their commits were
  cherry-picked onto CodeHealth, and the worktrees removed.
- The commits: one module or tight group each, 35 in all.

How it was checked:
- Per commit: an AST comparison with a273bf1, ignoring docstrings and comments.
  Each changed block is named in the commit body.
- Over the whole package:
  - 19 modules have identical code;
  - in the other 43, no definition is added, removed or renamed;
  - all 75 explicit base-class calls that became `super()` reach the same
    defining class in their MRO, by a check that is shown to catch a mixin
    difference.
- The review checked every changed block by reading it, and a fresh-interpreter
  import of 53 modules, old against new. It also compared every unit
  conversion's outputs and an offscreen smoke run of 11 widget classes, and both
  were identical.

### Outcome

- labscript-utils 33dd7ca..b54e51a, 37 commits:
  - 33dd7ca: the PyQt6 inventory's build script in `docs/`, with conf.py's
    regenerate note.
  - 35 style commits, one per module or tight group.
  - b54e51a: `aom.py` keeps its numpy star import. Finding 2 explains why.
- What changed in code: only the allowed forms:
  - `class Foo:`, zero-argument `super()`, and f-strings with identical results;
  - scoped Qt enums, and `shotqueue.py`'s star imports qualified;
  - unused imports removed (elide_label's `QtGui`, setup_logging's
    `logging.handlers`, which every user imports itself);
  - private and local renames;
  - `Thread(daemon=True)`.
  - Public names, signatures and `__all__` are unchanged; a first-pass rename
    of five public methods was reverted.
- Rule 14: the JQI banner replaces Monash in the fork's plugins.py,
  lookup_format.py, file_utils.py and qtwidgets/shotqueue.py, and is added to
  toml_config.py. Upstream files keep their own.
- Held: plugins.py's `MenuContext` class and its module-docstring parts, byte
  for byte.
- Lines, non-blank: +1572 net.
  - Docstrings went from 1053 lines to 2800: NumPy docstrings on the public
    surface.
  - Comments fell from 1199 to 1090, and code from 5122 to 5013.
- Tests: labscript-utils passes 25 at b54e51a. Every consumer's suite passes on
  its CodeHealth against labscript-utils 20b58e6:
  - runmanager 139, blacs 68, lyse 44, labscript-devices 41;
  - labscript-optimization 216, labscript-agents 15, runviewer 10, labscript 3;
  - hyde's 17 plugin-related test files.
  - b54e51a restored `aom.py`'s star import, so behaviour stayed the same until
    c72cdc4 fixed SineAom's clamp.

### Findings

Seen during the pass. Every one is now fixed, recorded as a known issue, or
judged not a bug.
- The seven a user would see: fixed, in the next section.
- The trivial rest, fixed on CodeHealth in a35f8ea..58cd97d, one commit each.
  - Behaviour, each reproduced failing before and passing after:
    - the profile path None (a35f8ea);
    - InvertedDigitalOutput's '0' (fe380d8);
    - elide_label's mode check before it wraps the label (670699c);
    - frequency conversions extending a class-level derived_units
      (2aaab07);
    - quad_driver's A_from_base on arrays (53def07);
    - get_version on single-file modules (16b4e2f);
    - the header widgets after one without an indent (dad06a5).
  - Text: versions.py's missing import and dead fallback (dc9acf4); the
    shared-secret error's example in TOML (e7baae2); "occurred" (abe211f);
    shot_utils' banner (cc3eccd). example.toml documents the `[logging]` keys and
    `allow_insecure` at the values the code uses when they are omitted (81688e0).
  - LabConfig raises ValueError, not bare Exception (777aefc).
  - Dead code removed: imageoutput's store, the plugin key, Settings' pass
    statements, FileWatcher's always-true elif, `_MultiplicativeConversion.__get__`
    and double_import_denier's DEBUG switch (b7c547a..58cd97d).
- Needing thought, listed in `KNOWN_ISSUES.md`: settings' `eval`, the
  conversions' None calibration, OptotuneLens' default coefficients, Lock's
  `read_only` before connect, dragdroptab's group None, and app configs' dropped
  top-level scalars.
- Not bugs:
  - lookup_format catching only KeyError is Ian's step 1 decision (entry 35).
  - excepthook's window past `MAX_WINDOWS` is its documented notice that further
    errors will not be shown.
  - `FileWatcher.add_files` takes an iterable, as documented; upstream never
    promised a bare string.
  - quad_driver's `v_min` is unreachable only for its default parameters.
  - The offscreen `ToolPalette.hide()` crash seen in step 4's review did not
    reproduce, with or without focus inside the palette.
- Design questions for Ian rather than bugs:
  - re-export `populate_registry`, `BLACS_tab_registry` and `ClassRegister`
    from `device_registry`?

### Docstring trim and bug fixes

Ian's decisions on step 6, carried out on CodeHealth, 9a92102..9281c03.
- The docstring trim, by Ian's rule:
  - each docstring keeps its summary line;
  - a Parameters, Returns or Raises entry stays only where it says what the
    name, signature and summary do not;
  - a simple function's docstring is one line;
  - internal code gets one only when its name does not explain it.
  - Eight Sonnet workers in detached worktrees made 22 commits. d07c56b
    restores five facts that other repos rely on.
  - The code is AST-identical, except in the seven files the fixes changed.
  - plugins.py's held parts are unchanged.
  - Docstring lines went from 2800 to 1885; there were 1053 before step 6.
- The seven bugs, each reproduced failing before its fix and passing after:
  1. 1b6ebf8: the shot queue keeps a multi-row selection. `_select_rows` moves
     the current row through the selection model with `NoUpdate`. The view's
     `setCurrentIndex` had reselected by the keyboard modifiers held, so with
     none held it collapsed the selection to one row.
     - It was shown through runmanager's real queue widget, refreshed by
       Engage, by BLACS taking a shot, and by pause.
     - A user saw it at every `queueChanged`: each new shot, each shot BLACS
       took or finished, each finished compile and each pause toggle. Delete and
       Compile again then acted on one row.
     - 9281c03 adds a test, which fails on the old code.
  2. c72cdc4: SineAom clamps its lowest power at 0. aom.py imports only the numpy
     names it uses, so `max` is the builtin again, as under numpy 1.
  3. 3f9bc18: a bound FileWatcher callback is passed the arguments it takes,
     counted by signature.
  4. bebdbde: dragdroptab's 10-pixel leaving buffer applies to a tab widget that
     accepts drops anywhere.
  5. fcd22ab: h5_lock releases the kill lock when taking the zlock fails.
  6. 90e9e8c: setup_logging runs when `sys.stdout` is None.
  7. 266b8e6: interpreter start prints no traceback when the host name cannot be
     read or a legacy INI cannot be converted. The apps still raise it.
- UpstreamBugFixes, local and unpushed: 9edb6b5..379f8be holds fixes 2 to 7,
  each cherry-picked with -x and resolved against upstream's code. Each was
  shown failing at 086a267 and passing after. Fix 1's file is the fork's only.
- Tests: labscript-utils passes 26. Every consumer's suite passes on its
  CodeHealth against labscript-utils 1057a19:
  - runmanager 139, blacs 68, lyse 44, labscript-devices 41;
  - labscript-optimization 216, labscript-agents 15, runviewer 10, labscript 3;
  - hyde's 17 plugin-related test files.

## On merge

These describe Development, which still holds the code step 1 removed. Whoever
merges CodeHealth into Development updates them in the meta repo:

- `issues/server_interfaces_2026_09_25.md:112-113` lists `LinkIndicator`'s
  `interval=2` argument, now an attribute.
- `issues/blacs_issues_2026_08_28.md`, slice 11 (lines 294-306, 320-323), plans to
  silence plugin deprecation warnings that are gone, and requires upstream-style
  plugins to keep working, which Ian dropped.
- `issues/seen_while_mapping.md:40` names the duplicated `_is_accepted_path`,
  now removed.
- `CODEX.md:961-964` lists "icons" among `MenuContext`'s features.
- `labscript_project.md:97` says `qtwidgets/__init__.py` lazily re-exports the
  shot queue widget.
- `CODEX.md:958` and `985`, `issues/plugin_refactor_prd.md:83` and
  `issues/seen_while_mapping.md:14` and `21` name `get_callbacks`, now gone. So
  do labscript-library's `capabilities.md:76` and its inventory.

labscript-utils' `PluginManager` asks only for `get_event_handlers` (d515339).
blacs's CodeHealth, which renames its hooks to it (dee664a), merges with it:
alone, every BLACS plugin's event handlers are silently dropped.
