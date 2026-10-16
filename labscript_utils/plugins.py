#####################################################################
#                                                                   #
# /labscript_utils/plugins.py                                       #
#                                                                   #
# Copyright 2026, JQI                                               #
# Author: Ian Spielman                                              #
#                                                                   #
# This file is part of labscript-utils, in the labscript suite      #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################

"""Plugin discovery, instantiation, and hook routing for labscript apps.

The application owns where things go: menus, UI containers, notifications, and
where saved plugin state is stored. It chooses its events and when they fire.
The manager calls the plugins' hooks, routes their contributions to the contexts
the application registered, and fires an event to its handlers.

The usual package layout is::

    myapp/
        plugins/
            __init__.py
            example/
                __init__.py  # defines class Plugin

The module name becomes the plugin name. Another package can also ship a plugin
as an ``importlib.metadata`` entry point naming its module, in the group the
application gives the manager; the entry point's name is the plugin's. Each
plugin is built as ``Plugin()``, with no arguments, and subclasses
``BasePlugin``, overriding the hooks it needs. Its saved state goes out through
``get_save_data()`` and comes back through ``restore_save_data(data)``.

A plugin declares a named ``context`` for a UI contribution, and the application
registers objects that implement ``add(plugin_name, contribution, data)``. That
is the full shared UI contract; the module does not know where a plugin UI
lives. Menu contributions go to the context registered as ``menus``, normally a
``MenuContext``, which renders the actions of every plugin together once
contribution routing is complete.

Contribution menu skeleton with MenuContext
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``get_menu_contributions()`` returns dictionaries routed to the application
``menus`` context. ``MenuContext`` understands these keys:

* ``location``: app-registered top-level menu id, such as ``file`` or
  ``window``
* ``path``: optional submenu path below that location; defaults to ``()``
* ``group``: separator group within the same location/path; defaults to
  ``None``
* ``order``: numeric order within the group; defaults to ``DEFAULT_PRIORITY``
* ``name``: action text
* ``action``: callable connected to the action's ``triggered`` signal
* ``icon``: an icon, or what the context's ``icon_factory`` turns into one
* ``shortcut``, ``checkable``, and ``enabled``: optional action properties
  applied when the concrete action object supports them

``enabled`` may also be a zero-argument callable, for a contribution whose
availability depends on live application state rather than on a flag known when
the plugin is written. ``MenuContext.render()`` calls it once, at render time,
and applies ``bool()`` to the result. ``render()`` consumes the contributions it
draws, so a later render needs them added again; the dictionary keeps the
callable rather than its value, so that render evaluates it afresh. If the
callable raises, the action is disabled and the failure is logged: a
precondition that cannot be established should leave that one action reporting
itself unavailable, not abort the whole menu build. A non-callable ``enabled``
is applied to the action unchanged.

File-dialog-style plugin example::

    class FileDialogsPlugin(BasePlugin):
        def __init__(self):
            self.services = None

        def plugin_setup_complete(self, data):
            self.services = data['project_services']

        def get_menu_contributions(self):
            return [
                {
                    'location': 'file',
                    'group': 'project',
                    'order': 10,
                    'name': 'New Project',
                    'shortcut': 'Ctrl+N',
                    'action': self.new_project,
                },
                {
                    'location': 'file',
                    'group': 'project',
                    'order': 20,
                    'name': 'Open Project...',
                    'shortcut': 'Ctrl+O',
                    'action': self.open_project,
                },
                {
                    'location': 'file',
                    'group': 'save',
                    'order': 10,
                    'name': 'Save',
                    'shortcut': 'Ctrl+S',
                    'action': self.save_project,
                },
                {
                    'location': 'file',
                    'group': 'save',
                    'order': 20,
                    'name': 'Save As...',
                    'shortcut': 'Ctrl+Shift+S',
                    'action': self.save_project_as,
                },
                {
                    'location': 'file',
                    'group': 'application',
                    'order': 100,
                    'name': 'Quit',
                    'shortcut': 'Ctrl+Q',
                    'action': self.quit_application,
                },
            ]

        def new_project(self):
            self.services.new_project_dialog.open()

        def open_project(self):
            self.services.load_project_dialog.open()

        def save_project(self):
            self.services.save_project_command.execute()

        def save_project_as(self):
            self.services.save_as_project_dialog.open()

        def quit_application(self):
            self.services.quit_command.execute()

Expected UI result: the application renders the actions in its registered
``file`` menu, creates separators between the ``project``, ``save``, and
``application`` groups, and applies shortcuts without the shared framework
knowing what a project is.

The application side of the contribution path::

            menus = MenuContext(logger=self.logger)
            menus.register_location('file', self.file_menu)
            menus.register_location('window', self.window_menu)

            self.plugin_manager.register_context('menus', menus)
            self.plugin_manager.setup_contexts(self.app_data)
            menus.render()
"""

import importlib
import importlib.metadata
import logging
import os
from types import MethodType


DEFAULT_PRIORITY = 10
DEFAULT_SETUP_PRIORITY = 0

__all__ = [
    'DEFAULT_PRIORITY',
    'DEFAULT_SETUP_PRIORITY',
    'Callback',
    'callback',
    'BasePlugin',
    'MenuContext',
    'PluginManager',
]


class Callback:
    """Wrap a callable with priority metadata and method-style binding.

    ``PluginManager.get_event_handlers()`` sorts the callbacks for an event by
    ``priority``, lowest first. A ``Callback`` stored as a class attribute binds
    to the plugin instance like a method.
    """
    def __init__(self, func, priority=DEFAULT_PRIORITY):
        self.priority = priority
        self.func = func

    def __get__(self, instance, class_):
        if instance is None:
            return self
        else:
            return MethodType(self, instance)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class callback:
    """Decorator that turns a function into a :class:`Callback`."""
    def __init__(self, priority=DEFAULT_PRIORITY):
        self.priority = priority

    def __call__(self, func):
        return Callback(func, self.priority)


class BasePlugin:
    """The plugin interface, every hook a no-op.

    A plugin subclasses it and overrides the hooks it needs. It may also define
    ``plugin_setup_complete(data)`` or ``get_setup_activities()``, which
    :meth:`PluginManager.setup_complete` calls.
    """

    def get_event_handlers(self):
        """Return a mapping of event names to handlers.

        Event names are application-defined strings. Values may be plain
        callables or :class:`Callback` instances, which the manager sorts by
        ``priority``.
        """
        return {}

    def get_ui_contributions(self):
        """Return an iterable of UI contribution dictionaries.

        Each has a ``context`` key naming an application-registered context; the
        remaining keys are application-defined.
        """
        return []

    def get_menu_contributions(self):
        """Return an iterable of menu contribution dictionaries."""
        return []

    def get_services(self):
        """Return a mapping of service names to objects this plugin exposes."""
        return {}

    def get_save_data(self):
        """Return the plugin's state to save, as data TOML can hold."""
        return {}

    def restore_save_data(self, data):
        """Restore the state ``get_save_data()`` returned, ``{}`` if none was saved."""

    def close(self):
        """Release what the plugin holds, at application shutdown."""


class MenuContext(object):
    """Collect and render contribution-based menu actions.

    Applications register stable top-level menu locations, such as ``file`` or
    ``tools``. Plugins contribute action dictionaries that request a location,
    optional submenu path, separator group, order, action text, and callback.
    Rendering is deferred until all plugins have contributed so ordering and
    group separators can be computed across plugins.
    """
    def __init__(self, logger=None, icon_factory=None):
        """Create a menu context.

        Parameters
        ----------
        logger : logging.Logger, optional
            Logger used for skipped or malformed menu contributions.
        icon_factory : callable, optional
            Turns a contribution's ``icon``, such as a resource name, into the
            icon set on its action. Without it the ``icon`` is set as given.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.icon_factory = icon_factory
        self.locations = {}
        self.contributions = []

    def register_location(self, name, menu):
        """Register an application-owned menu object as a stable location."""
        self.locations[name] = menu

    def add(self, plugin_name, contribution, data):
        """Collect one menu contribution for later rendering.

        ``data`` is accepted for the generic context contract. Menu
        contributions already contain their callbacks, so this context does not
        need to inspect app data directly.
        """
        self.contributions.append((plugin_name, contribution))

    def render(self):
        """Render all collected menu contributions into registered locations.

        Collected contributions are consumed, so calling this twice does not
        duplicate every menu entry.

        A contribution's ``enabled`` value may be a zero-argument callable,
        which is called here and its result applied as a boolean. A callable
        that raises disables that action and is logged, leaving the rest of the
        menu to build.
        """
        contributions, self.contributions = self.contributions, []
        grouped = {}
        group_orders = {}

        for plugin_name, contribution in contributions:
            if not isinstance(contribution, dict):
                self.logger.error(
                    "Menu contribution from plugin '%s' is not a dictionary. "
                    "Skipping." % plugin_name
                )
                continue
            if 'location' not in contribution:
                self.logger.error(
                    "Menu contribution from plugin '%s' missing location. "
                    "Skipping." % plugin_name
                )
                continue
            if 'name' not in contribution:
                self.logger.error(
                    "Menu contribution from plugin '%s' missing name. "
                    "Skipping." % plugin_name
                )
                continue

            location = contribution['location']
            if location not in self.locations:
                self.logger.error(
                    "Menu contribution from plugin '%s' requested unknown "
                    "location '%s'. Skipping." % (plugin_name, location)
                )
                continue

            path = contribution.get('path', ())
            if isinstance(path, str):
                path = (path,)
            else:
                path = tuple(path)

            key = (location, path)
            group_orders.setdefault(key, set()).add(contribution.get('group', None))
            grouped.setdefault(key, []).append((plugin_name, contribution))

        # Order groups by name rather than by the order plugins happened to be
        # discovered, which follows os.listdir() and so varies between machines.
        # An ungrouped contribution sorts first.
        group_orders = {
            key: {
                group: index
                for index, group in enumerate(
                    sorted(groups, key=lambda g: (g is not None, str(g)))
                )
            }
            for key, groups in group_orders.items()
        }

        menus = {}
        for name, menu in self.locations.items():
            menus[(name, ())] = menu

        for key in sorted(grouped):
            location, path = key
            parent_path = ()
            for submenu_name in path:
                submenu_path = parent_path + (submenu_name,)
                submenu_key = (location, submenu_path)
                if submenu_key not in menus:
                    menus[submenu_key] = menus[(location, parent_path)].addMenu(
                        submenu_name
                    )
                parent_path = submenu_path
            menu = menus[(location, path)]

            contributions = sorted(
                grouped[key],
                key=lambda item: (
                    group_orders[key][item[1].get('group', None)],
                    item[1].get('order', DEFAULT_PRIORITY),
                    item[0],
                    item[1]['name'],
                ),
            )

            previous_group = None
            for index, (plugin_name, contribution) in enumerate(contributions):
                group = contribution.get('group', None)
                if index and group != previous_group:
                    menu.addSeparator()
                previous_group = group

                name = contribution['name']
                action = menu.addAction(name)

                callback = contribution.get('action', None)
                if callback is not None:
                    action.triggered.connect(callback)

                icon = contribution.get('icon', None)
                if icon is not None and hasattr(action, 'setIcon'):
                    if self.icon_factory is not None:
                        icon = self.icon_factory(icon)
                    action.setIcon(icon)

                shortcut = contribution.get('shortcut', None)
                if shortcut is not None and hasattr(action, 'setShortcut'):
                    action.setShortcut(shortcut)

                checkable = contribution.get('checkable', False)
                if hasattr(action, 'setCheckable'):
                    action.setCheckable(checkable)

                # Resolved into a local: the contribution keeps the callable, so a
                # render after it is added again evaluates the precondition afresh.
                enabled = contribution.get('enabled', True)
                if callable(enabled):
                    try:
                        enabled = bool(enabled())
                    except Exception:
                        # A precondition that cannot be established must not
                        # take the rest of the menu down with it. Disabling is
                        # the safe reading: the action reports itself
                        # unavailable rather than offering an operation whose
                        # precondition is unknown.
                        enabled = False
                        self.logger.exception(
                            "Menu contribution '%s' from plugin '%s' raised "
                            "while resolving its 'enabled' callable. Disabling "
                            "the action." % (name, plugin_name)
                        )
                if hasattr(action, 'setEnabled'):
                    action.setEnabled(enabled)


class PluginManager:
    """Manage plugin discovery, lifecycle, events and saved state.

    An application creates one manager per plugin directory and calls
    ``discover_modules()``, ``instantiate_plugins()`` and
    ``restore_save_data()``, then ``collect_services()``, ``register_context()``
    and ``setup_contexts()``, then ``setup_complete()``. It fires its events with
    ``fire_event()``, saves with ``get_save_data()``, and calls
    ``close_plugins()`` at shutdown.
    """
    def __init__(
        self,
        plugin_package,
        plugins_dir,
        config=None,
        config_section=None,
        default_plugins=(),
        logger=None,
        entry_point_group=None,
    ):
        """Create a plugin manager.

        Parameters
        ----------
        plugin_package : str
            Import package containing plugin subpackages, for example
            ``'myapp.plugins'``.
        plugins_dir : str
            The folder of that package.
        config : optional
            Config object with ``has_section()``, ``add_section()``,
            ``has_option()``, ``set()``, and ``getboolean()`` methods, holding
            each plugin's enable flag in ``config_section``. Without it, every
            plugin found loads.
        config_section : str, optional
            The section of ``config`` holding the enable flags.
        default_plugins : iterable of str
            The plugins enabled when ``config`` has no flag for them yet.
        logger : logging.Logger, optional
        entry_point_group : str, optional
            The ``importlib.metadata`` entry-point group, such as
            ``'lyse.plugins'``, in which other packages name plugin modules.
        """
        self.plugin_package = plugin_package
        self.plugins_dir = plugins_dir
        self.config = config
        self.config_section = config_section
        self.default_plugins = set(default_plugins)
        self.logger = logger or logging.getLogger(__name__)
        self.entry_point_group = entry_point_group
        self.modules = {}
        self.plugins = {}
        self.services = {}
        self.contexts = {}

    def discover_modules(self):
        """Find the plugins, update config defaults, and import enabled modules.

        The plugins are the folders in ``plugins_dir``, then the modules named
        by entry points in ``entry_point_group``; a folder wins over an entry
        point of the same name. A plugin with no enable flag gets one, true if
        its name is in ``default_plugins``. Only enabled plugins are imported, or
        every one without a config; an import failure is logged and the plugin
        skipped. Returns the modules by plugin name.

        Raises
        ------
        ValueError
            If an enable flag in the config is not a boolean.
        """
        module_names = {
            name: f'{self.plugin_package}.{name}'
            for name in os.listdir(self.plugins_dir)
            if os.path.isdir(os.path.join(self.plugins_dir, name))
            and name != '__pycache__'
        }
        if self.entry_point_group is not None:
            for entry_point in importlib.metadata.entry_points(
                group=self.entry_point_group
            ):
                module_names.setdefault(entry_point.name, entry_point.module)

        if self.config is not None and not self.config.has_section(
            self.config_section
        ):
            self.config.add_section(self.config_section)

        modules = {}
        for name, module_name in module_names.items():
            if self.config is not None:
                # Keep the config in sync with the plugins present.
                if not self.config.has_option(self.config_section, name):
                    self.config.set(
                        self.config_section, name, name in self.default_plugins
                    )
                if not self.config.getboolean(self.config_section, name):
                    continue
            try:
                modules[name] = importlib.import_module(module_name)
            except Exception:
                self.logger.exception(f"Could not import plugin '{name}'. Skipping.")

        self.modules = modules
        return modules

    def instantiate_plugins(self):
        """Build ``module.Plugin()`` for each imported module.

        Instantiation failures are logged and skipped. Returns the instances by
        plugin name.
        """
        plugins = {}
        for module_name, module in self.modules.items():
            try:
                plugins[module_name] = module.Plugin()
            except Exception:
                self.logger.exception(
                    f"Could not instantiate plugin '{module_name}'. Skipping"
                )

        self.plugins = plugins
        return plugins

    def register_context(self, name, context):
        """Register an application-owned plugin contribution context.

        A context is any object with ``add(plugin_name, contribution, data)``.
        UI contributions go to the context named by their ``context`` key, and
        menu contributions to the context registered as ``'menus'``.
        """
        self.contexts[name] = context

    def _get_contributions(self, hook, module_name, label):
        """Return a plugin's contributions as a list, logging a hook that raises."""
        if hook is None:
            return []

        try:
            return list(hook() or ())
        except Exception:
            self.logger.exception(
                f"Error getting {label} contributions from plugin '{module_name}'. "
                "Skipping."
            )
            return []

    def setup_contexts(self, data):
        """Route plugin-declared UI and menu contributions to app contexts.

        A contribution for an unregistered context, or whose context raises in
        ``add()``, is logged and skipped.
        """
        for module_name, plugin in self.plugins.items():
            ui_contributions = self._get_contributions(
                getattr(plugin, 'get_ui_contributions', None),
                module_name,
                'UI',
            )

            for contribution in ui_contributions:
                try:
                    self.contexts[contribution['context']].add(
                        module_name, contribution, data
                    )
                except Exception:
                    self.logger.exception(
                        f"Error adding UI contribution from plugin '{module_name}'. "
                        "Skipping."
                    )

            menu_contributions = self._get_contributions(
                getattr(plugin, 'get_menu_contributions', None),
                module_name,
                'menu',
            )

            for contribution in menu_contributions:
                try:
                    self.contexts['menus'].add(module_name, contribution, data)
                except Exception:
                    self.logger.exception(
                        f"Error adding menu contribution from plugin '{module_name}'. "
                        "Skipping."
                    )

    def collect_services(self, base_services=None):
        """Merge app-owned and plugin-owned services into one registry.

        Returns the merged dict, also kept as ``services``.

        Raises
        ------
        ValueError
            If a plugin offers a service name that the application or an
            earlier plugin has already registered.
        """
        services = dict(base_services or {})

        for module_name, plugin in self.plugins.items():
            if not hasattr(plugin, "get_services"):
                continue

            try:
                plugin_services = dict(plugin.get_services())
            except Exception:
                self.logger.exception(
                    f"Error getting services from plugin '{module_name}'. Skipping."
                )
                continue

            for service_name in plugin_services:
                if service_name in services:
                    raise ValueError(
                        f"Plugin '{module_name}' offers service '{service_name}', "
                        "which is already registered."
                    )
            services.update(plugin_services)

        self.services = services
        return services

    def setup_complete(self, data):
        """Run plugin setup activities after application startup.

        ``get_setup_activities()`` returns records with ``name``, ``priority``
        and ``action``; a plugin without it contributes
        ``plugin_setup_complete`` as one activity at ``DEFAULT_SETUP_PRIORITY``.
        Activities from all plugins run lowest priority first, ties in plugin
        name order, each action called with ``data``. A failing action is
        logged and the rest still run; a plugin whose records are malformed is
        skipped whole.
        """
        setup_activities = []

        for module_name, plugin in self.plugins.items():
            try:
                if hasattr(plugin, 'get_setup_activities'):
                    plugin_activities = plugin.get_setup_activities()
                elif hasattr(plugin, 'plugin_setup_complete'):
                    plugin_activities = [
                        {
                            'name': 'plugin_setup_complete',
                            'priority': DEFAULT_SETUP_PRIORITY,
                            'action': plugin.plugin_setup_complete,
                        },
                    ]
                else:
                    continue

                # Built in full before it is added, so a bad record skips the
                # whole plugin rather than leaving it half set up.
                setup_activities.extend([
                    {
                        'module_name': module_name,
                        'name': activity['name'],
                        'priority': activity['priority'],
                        'action': activity['action'],
                    }
                    for activity in plugin_activities
                ])
            except Exception:
                self.logger.exception(
                    f"Error getting setup activities from plugin '{module_name}'. "
                    "Skipping."
                )

        setup_activities.sort(
            key=lambda activity: (activity['priority'], activity['module_name'])
        )

        for activity in setup_activities:
            module_name = activity['module_name']
            activity_name = activity['name']
            action = activity['action']
            try:
                action(data)
            except Exception:
                self.logger.exception(
                    f"Error in setup activity '{activity_name!s}' for plugin "
                    f"'{module_name}'. Plugin may not be functional."
                )

    def get_event_handlers(self, name):
        """Return all event handlers registered for ``name``, sorted by priority."""
        callbacks = []

        for plugin in self.plugins.values():
            try:
                hook = getattr(plugin, 'get_event_handlers', None)
                plugin_callbacks = hook() if hook is not None else None
                if plugin_callbacks and name in plugin_callbacks:
                    callbacks.append(plugin_callbacks[name])
            except Exception:
                self.logger.exception(f'Error getting callbacks from {plugin!s}.')

        callbacks.sort(
            key=lambda callback: getattr(callback, 'priority', DEFAULT_PRIORITY)
        )
        return callbacks

    def fire_event(self, name, *args, **kwargs):
        """Call every handler for the event ``name``, lowest priority first.

        A handler that raises is logged, and the rest still run.

        Returns
        -------
        list
            The handlers' results, in the order they ran, leaving out any that
            raised.
        """
        results = []
        for handler in self.get_event_handlers(name):
            try:
                results.append(handler(*args, **kwargs))
            except Exception:
                # Not an f-string: the unformatted message must be the same for
                # every event, since hyde reports each distinct one once.
                self.logger.exception("Error in a plugin's handler for '%s'.", name)
        return results

    def get_save_data(self):
        """Return ``{plugin name: data}`` from each plugin's ``get_save_data()``.

        A plugin that returns nothing is left out, as is one that raises, which
        is logged.
        """
        save_data = {}
        for module_name, plugin in self.plugins.items():
            try:
                data = plugin.get_save_data()
            except Exception:
                self.logger.exception(
                    f"Could not get save data from plugin '{module_name}'. Skipping."
                )
                continue
            if data:
                save_data[module_name] = data
        return save_data

    def restore_save_data(self, saved):
        """Hand each plugin its part of what ``get_save_data()`` returned.

        A plugin with no part gets ``{}``. A plugin that raises is logged, and
        the rest are still restored.
        """
        for module_name, plugin in self.plugins.items():
            try:
                plugin.restore_save_data(saved.get(module_name, {}))
            except Exception:
                self.logger.exception(
                    f"Could not restore the saved data of plugin '{module_name}'."
                )

    def close_plugins(self):
        """Call ``close()`` on every plugin during application shutdown."""
        for module_name, plugin in self.plugins.items():
            try:
                plugin.close()
            except Exception as e:
                self.logger.error(
                    f'Could not close plugin {module_name}. Error was: {e!s}'
                )
