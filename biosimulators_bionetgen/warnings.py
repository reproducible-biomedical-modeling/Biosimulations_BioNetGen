""" Warnings

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

__all__ = ['BioNetGenWarning', 'IgnoredBnglFileContentWarning']


class BioNetGenWarning(UserWarning):
    """ Base class for warnings """
    pass  # pragma: no cover


class IgnoredBnglFileContentWarning(BioNetGenWarning):
    """ Warning for content of a BNGL file that is ignored """
    pass  # pragma: no cover
