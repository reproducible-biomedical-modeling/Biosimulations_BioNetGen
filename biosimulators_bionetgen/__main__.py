""" BioSimulators-compliant command-line interface to the `BioNetGen <https://bionetgen.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, BioSimulators
:License: MIT
"""

from ._version import __version__
from .core import exec_sedml_docs_in_combine_archive
from .utils import get_bionetgen_version
from biosimulators_utils.simulator.cli import build_cli

App = build_cli('bionetgen', __version__,
                'BioNetGen', get_bionetgen_version(), 'https://bionetgen.org',
                exec_sedml_docs_in_combine_archive)


def main():
    with App() as app:
        app.run()
