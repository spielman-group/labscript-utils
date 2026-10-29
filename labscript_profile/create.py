import sys
import os
import shutil
import keyword
import secrets
from pathlib import Path
import h5py
from zprocess.security import generate_shared_secret
from labscript_profile import (
    LABSCRIPT_SUITE_PROFILE,
    default_labconfig_path,
    legacy_labconfig_path,
)
import argparse
from labscript_profile.toml_config import dump_toml_file, load_toml_file

_here = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILE_CONTENTS = os.path.join(_here, 'default_profile')


def _replace_backslashes(value):
    if isinstance(value, dict):
        return {key: _replace_backslashes(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_replace_backslashes(child) for child in value]
    if isinstance(value, str):
        return value.replace('\\', os.path.sep)
    return value


def write_shared_secret(shared_secret, directory):
    """Write a zprocess shared secret to a new file in a directory, and return its path."""
    path = Path(directory, f'zpsecret-{secrets.token_hex(4)}.key')
    path.write_text(shared_secret)
    return path


def validate_apparatus_name(apparatus_name):
    """Raise ValueError unless the name can be a package in labscriptlib.

    That is, it must be a Python identifier that is not a keyword.
    """
    if not apparatus_name.isidentifier() or keyword.iskeyword(apparatus_name):
        raise ValueError(
            f"Apparatus name {apparatus_name!r} is not a valid Python identifier. The "
            "apparatus name is the name of a package in labscriptlib, so it must consist "
            "of letters, digits and underscores, must not start with a digit, and must "
            "not be a Python keyword."
        )


def make_labconfig_file(shared_secret, apparatus_name=None):
    """Create the labconfig file from the profile's ``labconfig/example.toml``.

    ``shared_secret`` is written to a file beside it.

    Raises
    ------
    FileExistsError
        If a labconfig file already exists for this machine.
    """
    source_path = os.path.join(LABSCRIPT_SUITE_PROFILE, 'labconfig', 'example.toml')
    target_path = default_labconfig_path()
    # LEGACY INI COMPATIBILITY. DEPRECATED CODE, WILL BE REMOVED.
    legacy_path = legacy_labconfig_path()
    if os.path.exists(target_path) or (legacy_path is not None and os.path.exists(legacy_path)):
        raise FileExistsError(target_path)
    config = load_toml_file(source_path)
    if os.path.sep != '\\':
        config = _replace_backslashes(config)
    if sys.platform != 'win32':
        # Empty, so that the operating system's default programs open the files:
        config['programs']['text_editor'] = ''
        config['programs']['hdf5_viewer'] = ''
        config['default']['shared_drive'] = '$HOME/labscript_shared'
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shared_secret_path = write_shared_secret(shared_secret, target_path.parent)
    shared_secret_entry = Path(
        '%(labscript_suite)s', shared_secret_path.relative_to(LABSCRIPT_SUITE_PROFILE)
    )
    config['security']['shared_secret'] = str(shared_secret_entry)
    if apparatus_name is not None:
        print(f"\tSetting apparatus name to '{apparatus_name}'")
        config['default']['apparatus_name'] = apparatus_name

    dump_toml_file(target_path, config)


def make_runmanager_config_file():
    """Write runmanager's saved configuration, opening the example experiment.

    It is written where the labconfig's ``autoload_config_file`` says, so that
    runmanager opens the example experiment on its first run.
    """
    from labscript_utils.labconfig import LabConfig, save_appconfig

    config = LabConfig()
    config_path = os.path.expandvars(config.get('runmanager', 'autoload_config_file'))
    labscriptlib = os.path.expandvars(config.get('DEFAULT', 'labscriptlib'))
    save_appconfig(
        config_path,
        {
            'runmanager_state': {
                'current_labscript_file': str(Path(labscriptlib, 'example_experiment.py')),
                'is_using_default_shot_output_folder': True,
            }
        },
    )


def compile_connection_table():
    """Compile the connection table defined in the labconfig file.

    The output is placed in the location defined by the labconfig file. Nothing
    is compiled if runmanager cannot be imported.
    """
    try:
        import runmanager
    except ImportError:
        # if runmanager doesn't import, skip compilation
        return

    from labscript_utils.labconfig import LabConfig

    config = LabConfig()

    script_path = os.path.expandvars(config['paths']['connection_table_py'])
    output_h5_path = os.path.expandvars(config['paths']['connection_table_h5'])
    Path(output_h5_path).parent.mkdir(parents=True, exist_ok=True)
    # The compile reads the run file's globals, so it needs the group, empty here.
    with h5py.File(output_h5_path, 'w') as f:
        f.create_group('globals')

    def dummy_callback(success):
        pass

    runmanager.compile_labscript_async(labscript_file=script_path,
                                       run_file=output_h5_path,
                                       stream_port=None,
                                       done_callback=dummy_callback)
    print(f'\tOutput written to {output_h5_path}')


def create_profile_cli():
    """Run the ``labscript-profile-create`` command."""
    parser = argparse.ArgumentParser(prog='labscript-profile-create',
                                     description='Initialises a default labscript profile'
                                     )

    parser.add_argument('-n', '--apparatus_name',
                        type=str,
                        help='Sets the apparatus_name in the labconfig file and the name '
                             'of the apparatus package in labscriptlib. Must be a valid '
                             'Python identifier: letters, digits and underscores, not '
                             'starting with a digit, and not a Python keyword. Defaults '
                             'to example_apparatus',
                        )
    parser.add_argument('-c', '--compile',
                        action='store_true',
                        help='Enables compilation of the default example connection table',
                        default=False)

    args = parser.parse_args()

    if args.apparatus_name is not None:
        try:
            validate_apparatus_name(args.apparatus_name)
        except ValueError as e:
            parser.error(str(e))

    create_profile(args.apparatus_name, args.compile)


def create_profile(apparatus_name=None, compile_table=False):
    """Create a labscript profile from the default profile.

    Parameters
    ----------
    apparatus_name : str, optional
        Apparatus name to define in the config. If None, the default config file's
        name, example_apparatus, is kept.

    Raises
    ------
    FileExistsError
        If the profile directory already contains any item of the default profile.
    ValueError
        If ``apparatus_name`` is not a Python identifier, or is a keyword.
    zprocess.security.CurveNotSupported
        If libzmq has no CurveZMQ, so no shared secret can be made.
    """
    if apparatus_name is not None:
        validate_apparatus_name(apparatus_name)
    # Made before anything is written, so that a failure leaves no partial profile:
    shared_secret = generate_shared_secret()

    src = Path(DEFAULT_PROFILE_CONTENTS)
    dest = Path(LABSCRIPT_SUITE_PROFILE)
    print(f'Creating labscript profile at {LABSCRIPT_SUITE_PROFILE}')
    # Profile directory may exist already, but we will error if it contains any of the
    # sub-directories we want to copy into it:
    os.makedirs(dest, exist_ok=True)
    # Preferable to raise errors if anything exists before copying anything, rather than
    # do a partial copy before hitting an error:
    for src_file in src.iterdir():
        dest_file = dest / src_file.name
        if dest_file.exists():
            raise FileExistsError(dest_file)
    for src_file in src.iterdir():
        dest_file = dest / src_file.name
        if src_file.is_dir():
            shutil.copytree(src_file, dest_file)
        else:
            shutil.copy2(src_file, dest_file)

    print('Writing labconfig file')
    make_labconfig_file(shared_secret, apparatus_name)

    if apparatus_name is not None:
        print('\tRenaming apparatus directories')
        for path in dest.glob('**/example_apparatus/'):
            new_path = Path(str(path).replace('example_apparatus', apparatus_name))
            path.rename(new_path)

    print('Writing runmanager configuration file')
    make_runmanager_config_file()

    if compile_table:
        print('Compiling the example connection table')
        compile_connection_table()
