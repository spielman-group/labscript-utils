# labscript-utils test contract

A planning document for step 1 of the code-health campaign
(`issues/code_health_campaign.md` in the meta repo). It lists what each existing
test protects, for Ian's review, and is deleted when the revisions it leads to
are done.

Marks:

- **keep**: protects a real behaviour, and fails when that behaviour breaks.
- **rename**: keep, under a name that states the behaviour.
- **fix**: the behaviour is real, but the test cannot fail when it breaks.
- **cut**: protects nothing on the list; the category is given.

"Step 2.1" marks a test that guards behaviour no one asked for: not upstream's,
and reached by no user action or real caller. It is evidence for the deep pass,
not a decision.

Every fix and every cut was checked by breaking the behaviour by hand in a
scratch copy and running the test. "Broke X: passed" means the test did not
notice.

## Totals

- Test files: 6, plus `conftest.py`, which holds no tests.
- Tests: 49.
- Lines: 1590 in `tests/`, against 11575 core lines in `labscript_utils` and
  `labscript_profile`.
- Marks: keep 14, rename 10, fix 5, cut 20.

## A decision the list depends on

Seven tests of the base `MenuContext.render` are cut as unreachable. blacs builds
its menus with `MenuBuilder`, and hyde's `HydeMenuContext` overrides `render`
without calling `super()`. hyde does use the base class's `__init__`,
`register_location` and `add`. If the base `render` stays, these become keeps,
and the first also needs a fix: it cannot see the `order` key being ignored.

## tests/test_excepthook.py

- The six `TestEnvironmentFlag` tests checked the private
  `_no_error_dialog_from_env`, never the module's `NO_ERROR_DIALOG`. Hard-coding
  `NO_ERROR_DIALOG` to `True`, then `False`, left all seven excepthook tests
  passing. Ian decided the dialog is off only when `LABSCRIPT_NO_ERROR_DIALOG` is
  exactly `'1'`, which is all any repository sets. So they become one test of the
  real setting, read in a fresh process: `'1'` suppresses the dialog, and unset
  does not.
  - `test_unset_leaves_the_dialog_enabled`: **fix**, into that test.
  - `test_values_that_read_as_false_leave_the_dialog_enabled`: **fix**, into
    that test. Whether to test `'0'` as well is Ian's to decide.
  - `test_values_that_read_as_true_suppress_the_dialog`: **fix**, into that test.
  - `test_case_and_surrounding_whitespace_do_not_matter`: **cut**: only `'1'`
    suppresses now.
  - `test_an_unrecognised_value_suppresses_the_dialog`: **cut**: likewise.
  - `test_the_conftest_setting_used_across_the_suite_suppresses_it`: **cut**
    (duplicate of `'1'`).
- `TestTheFlagIsReadWhenUsed.test_tkhandler_consults_the_attribute_rather_than_a_captured_value`:
  an unhandled exception opens the dialog unless `NO_ERROR_DIALOG` is set, and
  assigning it takes effect at once. **rename** →
  `test_assigning_no_error_dialog_switches_the_error_dialog_on_and_off`. It is
  the only test that the dialog opens at all.

## tests/test_link_indicator.py

- `test_indicator_follows_a_server_answering_and_then_gone`: the light reads
  Responding while its server answers, passes each answer to `on_answer`, and
  reads Not responding, with the reason, once the server goes away. **keep**.

## tests/test_ls_zprocess.py

- `test_a_bound_client_reaches_its_servers_handler`: a client bound by `server`
  and `default_port` finds its server through the labconfig and gets its
  handler's answer. **keep**.
- `test_a_handler_exception_reaches_the_client_and_the_server_goes_on`: a handler's
  exception reaches the client as the same class and message, with the server's
  traceback, opens no dialog on the server, and the server keeps answering.
  **keep**.

## tests/test_plugins.py

- `test_callback_binds_as_method_and_keeps_priority`: an `@callback(priority=n)`
  method still binds to its plugin, and carries its priority. blacs uses it, and
  it is upstream blacs behaviour. **keep**.
- `test_base_plugin_defaults_are_no_ops`: a plugin that overrides no hook
  contributes nothing. **rename** →
  `test_a_plugin_that_overrides_nothing_contributes_nothing`. No `BasePlugin`
  subclass is driven through `setup_plugins`: blacs's plugins are
  `Plugin(object)`. Step 2.1.
- `test_discovery_defaults_config_and_imports_only_enabled_plugins`: discovery
  records each plugin directory in the config, enabled for the defaults, and
  imports only the enabled ones. **fix**: the disabled fixture raises on import,
  and the import guard swallows that. Broke the gate, `if enabled:` to
  `if True:`: passed. The config half is sound.
- `test_instantiate_plugins_uses_saved_settings`: each plugin is created with
  its saved settings. **keep**.
- `test_get_event_handlers_sorts_legacy_callbacks_by_priority_and_logs_errors`:
  `get_callbacks` handlers, which every blacs plugin has, run lowest priority
  first, and a raising plugin is skipped. **rename** →
  `test_legacy_get_callbacks_handlers_run_lowest_priority_first_and_a_raising_plugin_is_skipped`.
  Drop its log-wording assertion.
- `test_get_event_handlers_sorts_modern_handlers_by_priority`:
  `get_event_handlers` handlers, which hyde's plugins have, run lowest priority
  first across plugins. **keep**.
- `test_get_callbacks_warns_and_delegates_to_get_event_handlers`: the deprecated
  `PluginManager.get_callbacks()` forwards to `get_event_handlers()`. **cut**
  (agent-invented edge case): a pass-through with no caller. blacs's module
  `get_callbacks` calls `manager.get_event_handlers`. Step 2.1.
- `test_get_event_handlers_prefers_modern_hook_and_warns_for_legacy_one`: a plugin
  defining both hooks uses the new one, with one warning. **cut**
  (agent-invented edge case, and log wording): no plugin defines both. Step 2.1.
- `test_setup_plugins_prefers_modern_settings_callback_and_warns`: `setup_plugins`
  hands back each plugin's `settings_changed` handler, as blacs's
  connection_table and theme plugins use. **rename** →
  `test_setup_plugins_returns_each_plugins_settings_changed_handler`. Drop the
  both-hooks setup and the warning count. Step 2.1.
- `test_setup_plugins_warns_when_deprecated_menu_class_is_used`: a
  `get_menu_class()` plugin logs one deprecation warning. **cut** (log wording):
  its only assertion is the warning text. Broke menu building: passed.
- `test_get_event_handlers_logs_and_skips_malformed_event_handler_mappings`: a
  non-mapping from the hook is skipped and logged. **cut** (agent-invented edge
  case, and log wording): with the `Mapping` guard removed, the catch-all still
  skips and logs it; only the wording is pinned. Step 2.1.
- `test_menu_builder_creates_nested_menus_icons_actions_and_separators`: blacs's
  plugin menu dictionaries become nested menus with actions, icons and
  separators. Upstream blacs behaviour. **keep**.
- `test_setup_contexts_routes_ui_and_menu_contributions`: UI contributions go to
  the context they name, and menu contributions to `menus`, with the app data;
  this is hyde's path. **keep**.
- `test_setup_contexts_logs_and_skips_missing_unknown_and_broken_contexts`: seven
  kinds of bad contribution are logged and skipped. **cut** (log wording, and
  agent-invented edge cases): every assertion is log text, and four of the seven
  guards can be removed with the test still passing. Step 2.1.
- `test_menu_context_renders_locations_paths_groups_order_and_action_options`:
  `MenuContext.render` lays contributions out by location, path, group and
  order. **cut** (unreachable; see the decision above). Ignoring `order`: passed.
  Step 2.1.
- `test_menu_context_calls_callable_enabled_and_applies_the_result`: a callable
  `enabled` is resolved at render time. **cut** (unreachable; hyde resolves it in
  its own `resolve_menu_enabled`). Step 2.1.
- `test_menu_context_disables_the_action_when_enabled_callable_raises`: a raising
  `enabled` disables only that action. **cut** (unreachable, and log wording).
  Step 2.1.
- `test_menu_context_applies_non_callable_enabled_unchanged`: a fixed `enabled`
  flag is applied. **cut** (unreachable, and a duplicate of the render test).
  Step 2.1.
- `test_menu_context_does_not_cache_the_resolved_enabled_in_the_contribution`: a
  re-added contribution is evaluated afresh. **cut** (agent-invented edge case,
  and unreachable). Step 2.1.
- `test_base_plugin_exposes_no_services_by_default`: a plugin with no services
  offers none. **keep**.
- `test_collect_services_merges_base_and_plugin_services`: the service registry
  combines the application's services with every plugin's. hyde feeds every
  plugin from it. **keep**.
- `test_collect_services_skips_invalid_and_conflicting_entries`: the first
  plugin to offer a name keeps it, and a non-mapping is skipped. **cut** (log
  wording, and agent-invented edge case): hyde's service names are distinct, and
  "first" follows `os.listdir` order. Step 2.1.
- `test_legacy_plugin_setup_complete_runs_as_default_activity`: a `BasePlugin`'s
  `plugin_setup_complete(data)` is called with the app data. **cut** (duplicate
  of `test_setup_complete_runs_optional_argument_hook_once`, which fails under
  the same breaks).
- `test_duck_typed_plugin_setup_complete_still_runs`: a plugin without the base
  class gets `plugin_setup_complete(data)`, as every blacs plugin does.
  **rename** → `test_plugin_without_base_class_gets_setup_complete_with_app_data`.
- `test_multiple_setup_activities_run_in_priority_order`: a plugin's setup
  activities run lowest priority first, which hyde relies on. **fix**: the
  activities `early` and `late` also sort by name. Broke the sort, dropping
  priority from the key: all 35 tests passed. Fix by naming them so that name
  order and priority order differ.
- `test_setup_activity_ordering_is_deterministic_across_plugins`: activities of
  equal priority run in plugin-name order. **rename** →
  `test_equal_priority_setup_activities_run_in_plugin_name_order`.
- `test_setup_activity_names_break_priority_and_plugin_ties`: one plugin's
  activities of equal priority run in name order. **cut** (agent-invented edge
  case): no plugin has two at one priority. Step 2.1.
- `test_no_argument_plugin_setup_complete_fallback_still_runs`: an old
  `plugin_setup_complete()` with no argument is still called. Upstream blacs had
  this. **rename** →
  `test_plugin_setup_complete_without_argument_is_called_without_app_data`. Drop
  its log-wording assertion.
- `test_discover_modules_ignores_flags_that_are_not_booleans`: a non-boolean or
  inherited plugin flag does not stop discovery. A hand-written `theme = 1` once
  stopped BLACS starting. **rename** →
  `test_non_boolean_or_inherited_plugin_flag_does_not_stop_discovery`.
  Separately, "uses the default state" cannot fail: treating such a flag as
  enabled passed, because the fixture package does not exist.
- `test_discover_modules_keeps_a_flag_set_in_both_places`: discovery leaves a
  saved enable flag alone. **rename** →
  `test_discovery_keeps_an_enable_flag_already_in_the_config`.
- `test_discover_modules_seeds_flags_as_booleans`: first discovery writes real
  booleans. **cut** (duplicate of
  `test_discovery_defaults_config_and_imports_only_enabled_plugins`).
- `test_setup_complete_runs_optional_argument_hook_once`: a setup hook that
  raises is called once, not retried. Upstream blacs retried, and ran side
  effects twice. **rename** →
  `test_failing_plugin_setup_complete_is_called_only_once`.
- `test_empty_generator_contributions_do_not_report_a_missing_context`: an empty
  generator of menu contributions is not reported as missing `menus`. **cut**
  (log wording, and agent-invented edge case): the branch never runs, and with
  the message reworded the test passed. Step 2.1.
- `test_menu_context_group_order_is_independent_of_discovery_order`: base
  `render` orders groups by name. **cut** (unreachable; hyde tests this on
  `HydeMenuContext`). Step 2.1.
- `test_menu_context_render_is_idempotent`: a second base `render` does not
  duplicate entries. **cut** (unreachable; hyde keeps its contributions on
  purpose). Step 2.1.

## tests/test_shotqueue.py

- `test_row_background_colours_every_column_of_that_row`: a row's background
  colour, runmanager's state colours, fills every column, and other rows are
  left alone. **keep**.
- `test_a_struck_out_row_is_struck_out_in_every_column`: a struck-out row, a
  cancelled shot, is struck through in every column. **keep**.
- `test_the_rule_under_a_row_is_visible_on_a_dark_theme`: the rule under
  runmanager's sent-to-BLACS row can be seen on a dark theme. **keep**.

## tests/test_text_editor.py

- `test_a_file_opens_in_the_program_the_labconfig_names`: `open_in_editor`
  launches the labconfig's program with the file where `{file}` is, or first,
  and honours another program key such as `hdf5_viewer`. **keep**.

## Seen while listing: real behaviour no test guards

For information only. The contract adds no tests.

- **Plugin setup:** blacs's seven plugins rely on `setup_plugins` building
  `get_menu_class` menus into the menubar, keeping the menu instance, and
  collecting settings pages. Removing each failed no test.
- **Client host:** a bound ZMQClient's labconfig `servers` host is untested,
  because the test's host is the same as the `localhost` fallback.
- **Editor arguments:** `open_in_editor`'s `<program>_arguments` lookup is
  untested for any program but the text editor.
- **Light shutdown:** `LinkIndicator.shutdown()` dropping later answers is
  untested; a `shutdown()` that does nothing still passes.
- **Labconfig:** the `ls_zprocess` and `link_indicator` tests build `ZMQServer()`,
  which reads the machine's own labconfig security settings.
- **Stand-ins:** `FakeMenu`, `FakeAction` and `FakeSignal` imitate Qt menus, which
  rule 13 discourages.
