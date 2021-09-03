from ._version import __version__  # noqa: F401
# :obj:`str`: version

from .config import Config
from .core import exec_sed_task, preprocess_sed_task, exec_sed_doc, exec_sedml_docs_in_combine_archive  # noqa: F401

import subprocess


__all = [
    '__version__',
    'get_simulator_version',
    'exec_sed_task',
    'preprocess_sed_task',
    'exec_sed_doc',
    'exec_sedml_docs_in_combine_archive',
]


def get_simulator_version():
    """ Get the version of BioNetGen

    Returns:
        :obj:`str`: version
    """
    config = Config()
    return subprocess.check_output([config.bionetgen_path, '--version']).decode().strip().split(' ')[2]
