"""XDG Utilities"""

import errno
import getpass
import inspect
import os

import gutils.shared as shared

_user = getpass.getuser()


def getdir(userdir, stack=None):
    """ Get XDG User Directory.

    Args:
        userdir (str): one of the four defined XDG user directories ('config', 'data', 'runtime',
            or 'cache').
        stack (optional): stack object (see inspect module)

    Returns:
        Full user directory path, as specified by the XDG standard.
    """
    userdir = userdir.lower()
    userdir_opts = {'config', 'data', 'runtime', 'cache'}
    if userdir not in userdir_opts:
        raise ValueError("Argument @userdir MUST be one of the following "
                         "options: {}".format(userdir_opts))

    getters = {'config': _getter_factory('XDG_CONFIG_HOME', '/home/{}/.config/{}'),
               'data': _getter_factory('XDG_DATA_HOME', '/home/{}/.local/share/{}'),
               'runtime': _getter_factory('XDG_RUNTIME_DIR', '/tmp/{}'),
               'cache': _getter_factory('XDG_CACHE_HOME', '/home/{}/.cache/{}')}

    if stack is None:
        stack = inspect.stack()

    return getters[userdir](stack)


def _getter_factory(envvar, dirfmt):
    """ Returns XDG getter function that serves to fetch some XDG standard directory.

    Args:
        envvar (str): one of the four defined XDG environment variables that correspond to the XDG
            user directories.
        dirfmt: format string used to model the default path for the given XDG user directory.

    Returns:
        Function that retrieves the full path for the desired XDG user directory.
    """
    def _getter(stack):
        scriptname = shared.scriptname(stack)

        if envvar in os.environ:
            xdg_dir = '{}/{}'.format(os.environ[envvar], scriptname)
        else:
            if dirfmt.count('{}') < 2:
                xdg_dir = dirfmt.format(scriptname)
            else:
                xdg_dir = dirfmt.format(_user, scriptname)

        _create_dir(xdg_dir)
        return xdg_dir
    return _getter


def _create_dir(directory):
    """ Create directory if it does not already exist.

    Args:
        directory: full directory path.
    """
    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
