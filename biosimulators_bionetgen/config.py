""" Configuration for BioSimulators-BioNetGen

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import os

__all__ = ['Config']


class Config(object):
    """ Configuration

    Attributes:
        bionetgen_path (:obj:`str`): path to BioNetGen executable
    """

    def __init__(self):
        self.bionetgen_path = os.getenv('BIONETGEN_PATH', 'BNG2.pl')
