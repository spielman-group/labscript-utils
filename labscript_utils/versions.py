#####################################################################
#                                                                   #
# versions.py                                                       #
#                                                                   #
# Copyright 2019, Chris Billington                                  #
#                                                                   #
# This file is part of the labscript suite (see                     #
# http://labscriptsuite.org) and is licensed under the Simplified   #
# BSD License. See the license.txt file in the root of the project  #
# for the full license.                                             #
#                                                                   #
#####################################################################
import sys
import os
from pathlib import Path
import importlib
import tokenize
import ast
import packaging.version

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata


class NotFound:
    """Returned by `get_version` for a package that is not installed."""


class NoVersionInfo:
    """Returned by `get_version` for a package whose version cannot be found."""


class VersionException(RuntimeError):
    """Raised by `check_version` when a package's version is not acceptable."""


class BrokenInstall(RuntimeError):
    """Raised when a package has more than one set of installed metadata."""


ERR_BROKEN_INSTALL = """Multiple metadata files for {package} found in {path}; cannot
reliably get version information. This indicates a previous version of the package was
not properly removed. You may want to uninstall the package, manually delete remaining
metadata files/folders, then reinstall the package.""".replace('\n', ' ')


def get_import_path(import_name):
    """Get the folder a module would be imported from, without importing it.

    For a package this is the folder containing the package.

    Raises
    ------
    ModuleNotFoundError
        If the module is not installed.
    NotImplementedError
        If the module is a namespace package, which is not supported.
    """
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        raise ModuleNotFoundError(import_name)
    location = spec.origin
    if location is None:
        # A namespace package
        msg = "Version checking of namespace packages not implemented"
        raise NotImplementedError(msg)
    if spec.parent:
        # A package:
        return os.path.dirname(os.path.dirname(location))
    else:
        # A single-file module:
        return os.path.dirname(location)


def _get_metadata_version(project_name, import_path):
    """Return the metadata version of ``project_name`` at ``import_path``, or None."""
    for finder in sys.meta_path:
        if hasattr(finder, 'find_distributions'):
            context = importlib_metadata.DistributionFinder.Context(
                name=project_name, path=[import_path]
            )
            dists = finder.find_distributions(context)
            dists = list(dists)
            if len(dists) > 1:
                msg = ERR_BROKEN_INSTALL.format(package=project_name, path=import_path)
                raise BrokenInstall(msg)
            if dists:
                return dists[0].version


def _get_literal_version(filename):
    """Return the ``__version__ = '<v>'`` literal in a source file, or None."""
    if not os.path.exists(filename):
        return None
    with open(filename, 'r') as f:
        try:
            tokens = list(tokenize.generate_tokens(f.readline))
        except tokenize.TokenError:
            tokens = []
        for i, token in enumerate(tokens[:-2]):
            token_type, token_str, _, _, _ = token
            if token_type == tokenize.NAME and token_str == '__version__':
                next_token_type, next_token_str, _, _, _ = tokens[i + 1]
                if next_token_type == tokenize.OP and next_token_str == '=':
                    next_next_token_type, next_next_token_str, _, _, _ = tokens[i + 2]
                    if next_next_token_type == tokenize.STRING:
                        try:
                            version = ast.literal_eval(next_next_token_str)
                            if version is not None:
                                return version
                        except (SyntaxError, ValueError):
                            continue


def package_version(package):
    """Return the version of a labscript suite package, for its ``__version__``.

    Each package's ``__init__`` sets ``__version__ = package_version(__package__)``,
    so `package` is already in ``sys.modules``. In a git checkout the version is
    setuptools_scm's, which names the commit; otherwise it is the installed
    distribution's, or None if there is none.
    """
    root = Path(sys.modules[package].__file__).parent.parent
    if (root / '.git').is_dir():
        # Imported here, so that an installed copy, which is no git checkout,
        # does not pay for it whenever labscript_utils is imported.
        import setuptools_scm

        return setuptools_scm.get_version(
            root,
            version_scheme='semver-pep440-release-branch',
            local_scheme='node-and-date',
        )
    try:
        return importlib_metadata.version(package)
    except importlib_metadata.PackageNotFoundError:
        return None


def get_version(import_name, project_name=None, import_path=None):
    """Return the version of a package without importing it.

    Look, in order, for a setuptools_scm version, installed metadata for
    ``project_name``, a ``__version__.py`` file, and a ``__version__`` literal in
    the package source.

    Parameters
    ----------
    project_name : str, optional
        The package name, as given to pip. Must be specified if it differs from
        `import_name`.
    import_path : str, optional
        The folder containing the installed package. Default is where
        `get_import_path` finds it.

    Returns
    -------
    str or NotFound or NoVersionInfo
        The version. `NotFound` is returned if the package cannot be found, and
        `NoVersionInfo` if no version is found in the ways above, or if it is
        None.

    Raises
    ------
    NotImplementedError
        If `import_name` contains a period, or is a namespace package.
    BrokenInstall
        If the package has more than one set of installed metadata.
    """
    if project_name is None:
        project_name = import_name
    if '.' in import_name:
        msg = "Version checking of top-level packages only implemented"
        raise NotImplementedError(msg)
    if import_path is None:
        # Find the path where the module lives:
        try:
            import_path = get_import_path(import_name)
        except ImportError:
            return NotFound
    if not os.path.exists(os.path.join(import_path, import_name)):
        return NotFound
    import setuptools_scm

    try:
        # Check if setuptools_scm gives us a version number, for the case that it's a
        # git repo or PyPI tarball:
        return setuptools_scm.get_version(import_path)
    except LookupError:
        pass
    # Check if importlib_metadata knows about this module:
    version = _get_metadata_version(project_name, import_path)
    if version is not None:
        return version
    # Check if it has a version literal defined in a __version__.py file:
    version_dot_py = os.path.join(import_path, import_name, '__version__.py')
    version = _get_literal_version(version_dot_py)
    if version is not None:
        return version
    # check if it has a __version__ literal defined in its main module.
    pkg = os.path.join(import_path, import_name)
    if os.path.isdir(pkg):
        module_file = os.path.join(pkg, '__init__.py')
    else:
        module_file = pkg + '.py'
    version = _get_literal_version(module_file)
    if version is not None:
        return version
    return NoVersionInfo


def check_version(module_name, at_least, less_than, version=None, project_name=None):
    """Raise VersionException unless ``at_least <= version < less_than``.

    The version comes from :func:`get_version`, or from ``version``, for a package
    that stores it where `get_version` does not look. Pass ``project_name`` when it
    differs from ``module_name``, as for pyserial imported as 'serial'.
    VersionException is also raised if the module is not found or its version
    cannot be determined.
    """
    if version is None:
        version = get_version(module_name, project_name)

    if version is NotFound:
        raise VersionException(f'Module {module_name} not found')

    if version is NoVersionInfo:
        raise VersionException(f'Could not get version info from module {module_name}')

    at_least_version, less_than_version, installed_version = [
        packaging.version.parse(v) for v in [at_least, less_than, version]
    ]

    if not at_least_version <= installed_version < less_than_version:
        raise VersionException(
            f'{module_name} {version} found. '
            f'{at_least} <= {module_name} < {less_than} required.'
        )
