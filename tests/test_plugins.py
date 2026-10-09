import logging
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from labscript_utils.plugins import (
    BasePlugin,
    Callback,
    DEFAULT_SETUP_PRIORITY,
    MenuBuilder,
    PluginManager,
    callback,
)
from labscript_utils.labconfig import LabConfig


def make_labconfig(tmp_path, text=''):
    path = tmp_path / 'labconfig.toml'
    path.write_text(text)
    return LabConfig(config_path=path)


def test_callback_binds_as_method_and_keeps_priority():
    class Example(object):
        @callback(priority=5)
        def method(self, value):
            return self, value

    example = Example()

    assert isinstance(Example.__dict__['method'], Callback)
    assert Example.__dict__['method'].priority == 5
    assert example.method('value') == (example, 'value')


def test_a_plugin_that_overrides_nothing_contributes_nothing():
    plugin = BasePlugin({'x': 1})

    assert plugin.initial_settings == {'x': 1}
    assert plugin.get_menu_class() is None
    assert plugin.get_event_handlers() is None
    assert plugin.get_callbacks() is None
    assert plugin.get_ui_contributions() == []
    assert plugin.get_menu_contributions() == []


def make_plugin_package(tmp_path, modules):
    package = 'plugin_test_' + uuid.uuid4().hex
    package_dir = tmp_path / package
    plugins_dir = package_dir / 'plugins'
    plugins_dir.mkdir(parents=True)
    (package_dir / '__init__.py').write_text('')
    (plugins_dir / '__init__.py').write_text('')
    for name, source in modules.items():
        module_dir = plugins_dir / name
        module_dir.mkdir()
        (module_dir / '__init__.py').write_text(source)
    sys.path.insert(0, str(tmp_path))
    return package + '.plugins', plugins_dir


def make_manager(logger=None):
    return PluginManager(
        'package.plugins',
        'plugins',
        None,
        'app/plugins',
        logger=logger,
    )


class NoNotifications(object):
    def add_notification(self, notification_class):
        raise AssertionError('no notifications expected')

    def get_instance(self, notification_class):
        raise AssertionError('no notifications expected')


def test_discovery_defaults_config_and_imports_only_enabled_plugins(tmp_path):
    plugin_package, plugins_dir = make_plugin_package(
        tmp_path,
        {
            'enabled': 'class Plugin(object):\n    pass\n',
            'disabled': 'class Plugin(object):\n    pass\n',
        },
    )
    config = make_labconfig(tmp_path)
    manager = PluginManager(
        plugin_package,
        str(plugins_dir),
        config,
        'app/plugins',
        ['enabled'],
    )

    modules = manager.discover_modules()

    assert set(modules) == {'enabled'}
    assert config.get('app/plugins', 'enabled') is True
    assert config.get('app/plugins', 'disabled') is False


def test_instantiate_plugins_uses_saved_settings():
    class Plugin(object):
        def __init__(self, initial_settings):
            self.initial_settings = initial_settings

    manager = PluginManager(
        'package.plugins',
        'plugins',
        None,
        'app/plugins',
    )
    manager.modules = {'plugin': SimpleNamespace(Plugin=Plugin)}

    plugins = manager.instantiate_plugins({'plugin': {'answer': 42}})

    assert plugins['plugin'].initial_settings == {'answer': 42}


def test_legacy_get_callbacks_handlers_run_lowest_priority_first_and_a_raising_plugin_is_skipped():
    class Slow(object):
        def get_callbacks(self):
            return {'event': self.on_event}

        @callback(priority=20)
        def on_event(self):
            pass

    class Fast(object):
        def get_callbacks(self):
            return {'event': self.on_event}

        @callback(priority=5)
        def on_event(self):
            pass

    class Broken(object):
        def get_callbacks(self):
            raise RuntimeError('broken')

    manager = make_manager()
    manager.plugins = {
        'slow': Slow(),
        'broken': Broken(),
        'fast': Fast(),
    }

    callbacks = manager.get_event_handlers('event')

    assert [callback.priority for callback in callbacks] == [5, 20]


def test_get_event_handlers_sorts_modern_handlers_by_priority():
    class Slow(object):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=20)
        def on_event(self):
            pass

    class Fast(object):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=5)
        def on_event(self):
            pass

    manager = make_manager()
    manager.plugins = {
        'slow': Slow(),
        'fast': Fast(),
    }

    callbacks = manager.get_event_handlers('event')

    assert [callback.priority for callback in callbacks] == [5, 20]


def test_setup_plugins_returns_each_plugins_settings_changed_handler():
    class Plugin(BasePlugin):
        def get_setting_classes(self):
            return []

        def get_notification_classes(self):
            return []

        def set_notification_instances(self, notifications):
            pass

        def get_event_handlers(self):
            return {'settings_changed': self.settings_changed}

        @callback(priority=5)
        def settings_changed(self):
            pass

    manager = make_manager()
    manager.plugins = {'plugin': Plugin({})}

    _, settings_callbacks = manager.setup_plugins(
        data={},
        notifications=NoNotifications(),
        menu_builder=MenuBuilder(),
        menubar=FakeMenu(),
    )

    assert [callback.priority for callback in settings_callbacks] == [5]


class FakeSignal(object):
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeAction(object):
    def __init__(self, name, icon=None):
        self.name = name
        self.icon = icon
        self.triggered = FakeSignal()


class FakeMenu(object):
    def __init__(self, name='root'):
        self.name = name
        self.items = []

    def addMenu(self, name):
        menu = FakeMenu(name)
        self.items.append(('menu', menu))
        return menu

    def addAction(self, *args):
        if len(args) == 1:
            action = FakeAction(args[0])
        else:
            action = FakeAction(args[1], icon=args[0])
        self.items.append(('action', action))
        return action

    def addSeparator(self):
        self.items.append(('separator', None))


def test_menu_builder_creates_nested_menus_icons_actions_and_separators():
    root = FakeMenu()
    called = []

    def action():
        called.append(True)

    MenuBuilder(icon_factory=lambda name: 'icon:' + name).create_menu(
        root,
        {
            'name': 'Top',
            'menu_items': [
                {'name': 'Plain', 'action': action},
                {'separator': True},
                {'name': 'Icon', 'icon': 'resource', 'action': action},
            ],
        },
    )

    top = root.items[0][1]
    plain = top.items[0][1]
    icon = top.items[2][1]

    assert root.items[0][0] == 'menu'
    assert plain.name == 'Plain'
    assert plain.triggered.callbacks == [action]
    assert top.items[1] == ('separator', None)
    assert icon.name == 'Icon'
    assert icon.icon == 'icon:resource'
    assert icon.triggered.callbacks == [action]


class FakeContext(object):
    def __init__(self):
        self.items = []

    def add(self, plugin_name, contribution, data):
        self.items.append((plugin_name, contribution, data))


def test_setup_contexts_routes_ui_and_menu_contributions():
    class Plugin(object):
        def get_ui_contributions(self):
            return [{'context': 'mdi', 'key': 'browser'}]

        def get_menu_contributions(self):
            return [{'location': 'file', 'name': 'Open'}]

    mdi_context = FakeContext()
    menu_context = FakeContext()
    data = object()
    manager = PluginManager(
        'package.plugins',
        'plugins',
        None,
        'app/plugins',
    )
    manager.plugins = {'plugin': Plugin(), 'legacy': object()}
    manager.register_context('mdi', mdi_context)
    manager.register_context('menus', menu_context)

    manager.setup_contexts(data)

    assert mdi_context.items == [
        ('plugin', {'context': 'mdi', 'key': 'browser'}, data),
    ]
    assert menu_context.items == [
        ('plugin', {'location': 'file', 'name': 'Open'}, data),
    ]


class ServicePlugin(BasePlugin):
    def __init__(self, services):
        super().__init__({})
        self._services = services

    def get_services(self):
        return self._services


def test_base_plugin_exposes_no_services_by_default():
    plugin = BasePlugin({})

    assert plugin.get_services() == {}


def test_collect_services_merges_base_and_plugin_services():
    logger = logging.getLogger('test.plugins.services')
    manager = make_manager(logger=logger)
    manager.plugins = {
        'alpha': ServicePlugin({'answer': 42}),
        'beta': ServicePlugin({'greeter': str.upper}),
    }

    services = manager.collect_services({'execute_command': object()})

    assert 'execute_command' in services
    assert services['answer'] == 42
    assert services['greeter'] is str.upper
    assert manager.services is services


def test_plugin_without_base_class_gets_setup_complete_with_app_data():
    calls = []
    data = {'services': object()}

    class DuckTypedSetupPlugin(object):
        def plugin_setup_complete(self, setup_data):
            calls.append(('duck', setup_data))

    manager = make_manager()
    manager.plugins = {'duck': DuckTypedSetupPlugin()}

    manager.setup_complete(data)

    assert calls == [('duck', data)]


def test_multiple_setup_activities_run_in_priority_order():
    calls = []
    data = {'app': object()}

    class ActivityPlugin(BasePlugin):
        def get_setup_activities(self):
            # Named so that name order is the reverse of priority order.
            return [
                {
                    'name': 'a_late',
                    'priority': DEFAULT_SETUP_PRIORITY + 10,
                    'action': self.late,
                },
                {
                    'name': 'z_early',
                    'priority': DEFAULT_SETUP_PRIORITY - 10,
                    'action': self.early,
                },
            ]

        def early(self, setup_data):
            calls.append(('early', setup_data))

        def late(self, setup_data):
            calls.append(('late', setup_data))

    manager = make_manager()
    manager.plugins = {'activity': ActivityPlugin({})}

    manager.setup_complete(data)

    assert calls == [('early', data), ('late', data)]


def test_equal_priority_setup_activities_run_in_plugin_name_order():
    calls = []

    class NamedActivityPlugin(BasePlugin):
        def __init__(self, label):
            super().__init__({})
            self.label = label

        def get_setup_activities(self):
            return [
                {
                    'name': 'same_priority',
                    'priority': DEFAULT_SETUP_PRIORITY,
                    'action': self.record,
                },
            ]

        def record(self, data):
            del data
            calls.append(self.label)

    manager = make_manager()
    manager.plugins = {
        'zeta': NamedActivityPlugin('zeta'),
        'alpha': NamedActivityPlugin('alpha'),
    }

    manager.setup_complete({})

    assert calls == ['alpha', 'zeta']


def test_plugin_setup_complete_without_argument_is_called_without_app_data():
    calls = []

    class NoArgumentSetupPlugin(BasePlugin):
        def plugin_setup_complete(self):
            calls.append('legacy-no-arg')

    manager = make_manager()
    manager.plugins = {'legacy': NoArgumentSetupPlugin({})}

    manager.setup_complete({'unused': object()})

    assert calls == ['legacy-no-arg']

def _make_plugin_dirs(tmp_path, names):
    for name in names:
        (tmp_path / name).mkdir(parents=True)
    return str(tmp_path)


def test_non_boolean_or_inherited_plugin_flag_does_not_stop_discovery(tmp_path):
    """Neither an inherited config default nor a non-boolean flag stops discovery."""
    config = make_labconfig(
        tmp_path,
        "[default]\nuserlib = '/some/path/userlib'\n\n"
        "[\"app/plugins\"]\ntheme = 1\n",
    )
    plugins_dir = _make_plugin_dirs(tmp_path / 'plugins', ['userlib', 'theme'])
    manager = PluginManager(
        'package.plugins', plugins_dir, config, 'app/plugins',
        default_plugins=(), logger=logging.getLogger('test.plugins.discover.defaults'),
    )

    modules = manager.discover_modules()

    assert modules == {}
    assert config.get('app/plugins', 'userlib') is False
    assert config.get('app/plugins', 'theme') is False


def test_discovery_keeps_an_enable_flag_already_in_the_config(tmp_path):
    """A section option shadows the default, so an explicit flag still wins."""
    config = make_labconfig(
        tmp_path,
        "[default]\nuserlib = '/some/path/userlib'\n\n"
        "[\"app/plugins\"]\nuserlib = true\n",
    )
    plugins_dir = _make_plugin_dirs(tmp_path / 'plugins', ['userlib'])
    manager = PluginManager(
        'package.plugins', plugins_dir, config, 'app/plugins',
        default_plugins=(), logger=logging.getLogger('test.plugins.discover.both'),
    )

    manager.discover_modules()

    assert config.get('app/plugins', 'userlib') is True


def test_failing_plugin_setup_complete_is_called_only_once():
    """The BasePlugin signature must not be re-run by an old-API retry."""
    calls = []

    class OptionalArgumentPlugin(BasePlugin):
        def plugin_setup_complete(self, data=None):
            calls.append(data)
            raise RuntimeError('failed after the side effect')

    manager = make_manager(logger=logging.getLogger('test.plugins.setup.once'))
    manager.plugins = {'optional': OptionalArgumentPlugin({})}
    data = {'settings': object()}

    manager.setup_complete(data)

    assert calls == [data]
