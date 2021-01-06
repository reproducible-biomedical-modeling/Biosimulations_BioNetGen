""" Methods for reading BNGL models

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .data_model import Model, ModelBlock, Task
from .warnings import IgnoredBnglFileContentWarning
import pandas
import re
import warnings

__all__ = ['read_task', 'write_task', 'read_simulation_results']


def read_task(filename):
    """ Read a BNGL task from a file.

    Args:
       filename (:obj:`str`): path to the task

    Returns:
        :obj:`Task`: task

    Raises:
        :obj:`ValueError`: if the file is invalid
    """
    with open(filename, 'r') as file:
        task = Task()
        model = None
        current_block = None
        block_types = []

        for i_line, line in enumerate(file):
            # ignore comments and leading and trailing white space
            line = line.partition('#')[0].strip()
            line = re.sub(' +', ' ', line)

            # ignore blank and comment lines
            if not line:
                continue

            # handle starts of blocks
            if line.startswith('begin '):
                block_type = line.partition(' ')[2].lower()
                block_types.append(block_type)

                if block_type == 'model' and model is not None:
                    msg = ('`{}` contains a second model at line {}.').format(
                        filename, i_line + 1)
                    raise ValueError(msg)

                if model is None:
                    model = task.model = Model()

                if len(block_types) > 1 and block_types[0] != 'model':
                    msg = ('`{}` is inappropriately nested with `{}` at line {} of `{}`.').format(
                        block_type, block_types[0], i_line + 1, filename)
                    raise ValueError(msg)

                if len(block_types) > 2:
                    msg = ('`{}` is inappropriately nested with `{}` at line {} of `{}`.').format(
                        block_type, block_types[-2], i_line + 1, filename)
                    raise ValueError(msg)

                if block_type != 'model':
                    if block_type in model:
                        msg = ('`{}` has a second `{}` block at line {}.').format(
                            filename, block_types[-1], i_line + 1)
                        raise ValueError(msg)
                    current_block = model[block_type] = ModelBlock()

            # handle ends of blocks
            elif line.startswith('end '):
                end_block_type = line.partition(' ')[2]
                start_block_type = block_types.pop()
                if end_block_type != start_block_type:
                    msg = '`{}` block of `{}` incorrectly ends with `{}` at line {}.'.format(
                        start_block_type, filename, end_block_type, i_line + 1)
                    raise ValueError(msg)
                current_block = None

                if task.actions:
                    msg = 'Lines in `{}` outside content blocks were ignored\n:  `{}`'.format(
                        filename, '`\n  `'.join(task.actions))
                    warnings.warn(msg, IgnoredBnglFileContentWarning)
                    task.actions = []

            # handle the contents of blocks
            else:
                if current_block is not None:
                    current_block.append(line)

                else:
                    task.actions.append(line)

    if model is None:
        msg = '`{}` does not contain a model.'.format(filename)
        raise ValueError(msg)

    if block_types:
        msg = 'The `{}` block in `{}` has no termination`.'.format(block_types[-1], filename)
        raise ValueError(msg)

    return task


def write_task(task, filename):
    """ Write a BNGL task to a file

    Args:
        task (:obj:`Task`): task
        filename (:obj:`str`): path to save the model
    """
    with open(filename, 'w') as file:
        # write model to file
        if task.model:
            model = task.model
            file.write('begin model\n')
            for block_type, block_lines in model.items():
                file.write('begin {}\n'.format(block_type))
                for line in block_lines:
                    file.write('    {}\n'.format(line))
                file.write('end {}\n'.format(block_type))
            file.write('end model\n')

        # write actions to file
        for action in task.actions:
            file.write(action)
            file.write('\n')


def read_simulation_results(filename):
    """ Read the predicted time courses of the observables of a simulation

    Args:
        filename (:obj:`str`): path to simulation results in BioNetGen's gdat format

    Returns:
        :obj:`pandas.DataFrame`: predicted time courses of the observables
    """
    with open(filename, "r") as file:
        # Get column names from first line of file
        line = file.readline()
        names = re.split(r'\s+', (re.sub('#', '', line)).strip())

        # Read results
        return pandas.read_table(file, sep=r'\s+', header=None, names=names).transpose()
