import importlib
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
    MenuContext,
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
    plugin = BasePlugin()

    assert plugin.get_event_handlers() == {}
    assert plugin.get_ui_contributions() == []
    assert plugin.get_menu_contributions() == []
    assert plugin.get_services() == {}
    assert plugin.get_save_data() == {}


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


def make_entry_point(tmp_path, group, name):
    """Install a plugin module that a distribution names in ``group``."""
    site = tmp_path / 'site'
    module_name = 'entry_point_plugin_' + uuid.uuid4().hex
    (site / f'{module_name}-0.dist-info').mkdir(parents=True)
    (site / f'{module_name}-0.dist-info' / 'METADATA').write_text(
        f'Metadata-Version: 2.1\nName: {module_name}\nVersion: 0\n'
    )
    (site / f'{module_name}-0.dist-info' / 'entry_points.txt').write_text(
        f'[{group}]\n{name} = {module_name}\n'
    )
    (site / f'{module_name}.py').write_text('class Plugin(object):\n    pass\n')
    sys.path.insert(0, str(site))
    importlib.invalidate_caches()
    return module_name


def make_manager(logger=None):
    return PluginManager(
        'package.plugins',
        'plugins',
        None,
        'app/plugins',
        logger=logger,
    )


def test_discovery_defaults_config_and_imports_only_enabled_plugins(tmp_path):
    group = 'app_' + uuid.uuid4().hex
    make_entry_point(tmp_path, group, 'external')
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
        entry_point_group=group,
    )

    modules = manager.discover_modules()

    assert set(modules) == {'enabled'}
    assert config.get('app/plugins', 'enabled') is True
    assert config.get('app/plugins', 'disabled') is False
    assert config.get('app/plugins', 'external') is False


def test_without_a_config_every_plugin_found_loads(tmp_path):
    group = 'app_' + uuid.uuid4().hex
    external = make_entry_point(tmp_path, group, 'external')
    plugin_package, plugins_dir = make_plugin_package(
        tmp_path, {'local': 'class Plugin(object):\n    pass\n'}
    )
    manager = PluginManager(
        plugin_package, str(plugins_dir), entry_point_group=group
    )

    modules = manager.discover_modules()

    assert set(modules) == {'local', 'external'}
    assert modules['external'].__name__ == external


def test_plugin_state_saves_and_restores_through_the_manager():
    class Stateful(BasePlugin):
        def __init__(self):
            self.value = 0

        def get_save_data(self):
            return {'value': self.value}

        def restore_save_data(self, data):
            self.value = data.get('value', 0)

    class Broken(BasePlugin):
        def get_save_data(self):
            raise RuntimeError('broken')

        def restore_save_data(self, data):
            raise RuntimeError('broken')

    manager = PluginManager('package.plugins', 'plugins')
    manager.modules = {
        'broken': SimpleNamespace(Plugin=Broken),
        'plain': SimpleNamespace(Plugin=BasePlugin),
        'stateful': SimpleNamespace(Plugin=Stateful),
    }
    plugins = manager.instantiate_plugins()
    plugins['stateful'].value = 42

    saved = manager.get_save_data()
    plugins['stateful'].value = 0
    manager.restore_save_data(saved)

    assert saved == {'stateful': {'value': 42}}
    assert plugins['stateful'].value == 42


def test_an_event_reaches_its_handlers_lowest_priority_first_past_one_that_raises():
    class Slow(BasePlugin):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=20)
        def on_event(self, value):
            return ('slow', value)

    class Fast(BasePlugin):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=5)
        def on_event(self, value):
            return ('fast', value)

    class Raising(BasePlugin):
        def get_event_handlers(self):
            return {'event': self.on_event}

        @callback(priority=10)
        def on_event(self, value):
            raise RuntimeError('raising')

    class Broken(BasePlugin):
        def get_event_handlers(self):
            raise RuntimeError('broken')

    manager = make_manager()
    manager.plugins = {
        'slow': Slow(),
        'raising': Raising(),
        'broken': Broken(),
        'fast': Fast(),
    }

    assert manager.fire_event('event', 1) == [('fast', 1), ('slow', 1)]


class FakeSignal(object):
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class FakeAction(object):
    def __init__(self, name):
        self.name = name
        self.icon = None
        self.triggered = FakeSignal()

    def setIcon(self, icon):
        self.icon = icon


class FakeMenu(object):
    def __init__(self, name='root'):
        self.name = name
        self.items = []

    def addMenu(self, name):
        menu = FakeMenu(name)
        self.items.append(('menu', menu))
        return menu

    def addAction(self, name):
        action = FakeAction(name)
        self.items.append(('action', action))
        return action

    def addSeparator(self):
        self.items.append(('separator', None))


def test_a_menu_contributions_icon_comes_from_the_contexts_factory():
    file_menu = FakeMenu('file')
    menus = MenuContext(icon_factory=lambda name: 'icon:' + name)
    menus.register_location('file', file_menu)
    menus.add('plugin', {'location': 'file', 'name': 'Open', 'icon': 'folder'}, None)
    menus.add('plugin', {'location': 'file', 'name': 'Quit'}, None)

    menus.render()

    icons = {action.name: action.icon for kind, action in file_menu.items}
    assert icons == {'Open': 'icon:folder', 'Quit': None}


class FakeContext(object):
    def __init__(self):
        self.items = []

    def add(self, plugin_name, contribution, data):
        self.items.append((plugin_name, contribution, data))


def test_setup_contexts_routes_ui_and_menu_contributions():
    class Plugin(BasePlugin):
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
    manager.plugins = {'plugin': Plugin()}
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
        self._services = services

    def get_services(self):
        return self._services


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
    manager.plugins = {'activity': ActivityPlugin()}

    manager.setup_complete(data)

    assert calls == [('early', data), ('late', data)]


def test_equal_priority_setup_activities_run_in_plugin_name_order():
    calls = []

    class NamedActivityPlugin(BasePlugin):
        def __init__(self, label):
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


def _make_plugin_dirs(tmp_path, names):
    for name in names:
        (tmp_path / name).mkdir(parents=True)
    return str(tmp_path)


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
    """A plugin_setup_complete that raises is not called again."""
    calls = []

    class OptionalArgumentPlugin(BasePlugin):
        def plugin_setup_complete(self, data=None):
            calls.append(data)
            raise RuntimeError('failed after the side effect')

    manager = make_manager(logger=logging.getLogger('test.plugins.setup.once'))
    manager.plugins = {'optional': OptionalArgumentPlugin()}
    data = {'settings': object()}

    manager.setup_complete(data)

    assert calls == [data]
