""" BioSimulators-compliant command-line interface to the `BioNetGen <https://bionetgen.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-13
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from ._version import __version__
from .core import get_bionetgen_version, exec_sedml_docs_in_combine_archive
from biosimulators_utils.simulator.cli import build_cli
import subprocess

App = build_cli('bionetgen', __version__,
                'BioNetGen', get_bionetgen_version(), 'https://bionetgen.org',
                exec_sedml_docs_in_combine_archive)


def main():
    with App() as app:
        app.run()
