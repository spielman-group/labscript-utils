import sys
import os
import shutil
from pathlib import Path
from subprocess import check_output
import h5py
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


def make_shared_secret(directory):
    """Create a zprocess shared secret file in a directory.

    Parameters
    ----------
    directory : str or Path
        Directory to create the secret file in.

    Returns
    -------
    Path
        Path of the new secret file, as printed by ``zprocess.makesecret``.

    Raises
    ------
    RuntimeError
        If the output of ``zprocess.makesecret`` has no secret file path.
    """
    cmd = [sys.executable, '-m', 'zprocess.makesecret']
    output = check_output(cmd, cwd=directory).decode('utf8')
    for line in output.splitlines():
        if 'zpsecret' in line and '.key' in line:
            return Path(line.strip())
    raise RuntimeError("Could not parse output of zprocess.makesecret")


def make_labconfig_file(apparatus_name=None):
    """Create the labconfig file from the profile's ``labconfig/example.toml``.

    Parameters
    ----------
    apparatus_name : str, optional
        Overrides the default apparatus name with the provided one if not None.

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
    if sys.platform == 'linux':
        config['programs']['text_editor'] = 'gedit'
    elif sys.platform == 'darwin':
        config['programs']['text_editor'] = 'open'
        config['programs']['text_editor_arguments'] = '-a TextEdit {file}'
    if sys.platform != 'win32':
        config['programs']['hdf5_viewer'] = 'hdfview'
        config['default']['shared_drive'] = '$HOME/labscript_shared'
    shared_secret = make_shared_secret(target_path.parent)
    shared_secret_entry = Path(
        '%(labscript_suite)s', shared_secret.relative_to(LABSCRIPT_SUITE_PROFILE)
    )
    config['security']['shared_secret'] = str(shared_secret_entry)
    if apparatus_name is not None:
        print(f"\tSetting apparatus name to '{apparatus_name}'")
        config['default']['apparatus_name'] = apparatus_name

    target_path.parent.mkdir(parents=True, exist_ok=True)
    dump_toml_file(target_path, config)


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
    """Run the ``labscript-profile-create`` command.

    Parses command line arguments and calls :func:`~.create_profile`.
    """
    parser = argparse.ArgumentParser(prog='labscript-profile-create',
                                     description='Initialises a default labscript profile'
                                     )

    parser.add_argument('-n', '--apparatus_name',
                        type=str,
                        help='Sets the apparatus_name in the labconfig file. Defaults to example_apparatus',
                        )
    parser.add_argument('-c', '--compile',
                        action='store_true',
                        help='Enables compilation of the default example connection table',
                        default=False)

    args = parser.parse_args()

    create_profile(args.apparatus_name, args.compile)


def create_profile(apparatus_name=None, compile_table=False):
    """Create a labscript profile from the default profile.

    Parameters
    ----------
    apparatus_name : str, optional
        Apparatus name to define in the config. If None, the default config file's
        name, example_apparatus, is kept.
    compile_table : bool, optional
        Whether to compile the example connection table defined by the default
        config file. Default is False.

    Raises
    ------
    FileExistsError
        If the profile directory already contains any item of the default profile.
    """
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
    make_labconfig_file(apparatus_name)

    if apparatus_name is not None:
        print('\tRenaming apparatus directories')
        for path in dest.glob('**/example_apparatus/'):
            new_path = Path(str(path).replace('example_apparatus', apparatus_name))
            path.rename(new_path)

    if compile_table:
        print('Compiling the example connection table')
        compile_connection_table()
