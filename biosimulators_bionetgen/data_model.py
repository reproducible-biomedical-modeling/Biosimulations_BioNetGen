""" Data structures for representing BNGL models

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""
from biosimulators_utils.data_model import ValueType
from collections import OrderedDict

__all__ = ['Model', 'ModelBlock', 'Task', 'KISAO_SIMULATION_METHOD_ARGUMENTS_MAP']


class Model(OrderedDict):
    """ A BNGL model: a collection of model blocks """

    def is_equal(self, other):
        """ Determine whether two models are semantically equivalent

        Args:
            other (:obj:`Model`): second model

        Returns:
            :obj:`bool`: whether the models are semantically equivalent
        """
        if self.__class__ != other.__class__:
            return False

        self_keys = set()
        for key, lines in self.items():
            for line in lines:
                line = line.partition('#')[0].strip()
                if line:
                    self_keys.add(key)
                    break

        other_keys = set()
        for key, lines in other.items():
            for line in lines:
                line = line.partition('#')[0].strip()
                if line:
                    other_keys.add(key)
                    break

        if set(self.keys()) != set(other.keys()):
            return False

        for key in self.keys():
            if not self[key].is_equal(other[key]):
                return False

        return True


class ModelBlock(list):
    """ A "block" or section of a model such as `parameters` or 'molecule types' """

    def is_equal(self, other):
        """ Determine whether two model blocks are semantically equivalent

        Args:
            other (:obj:`ModelBlock`): second model block

        Returns:
            :obj:`bool`: whether the model blocks are semantically equivalent
        """
        if self.__class__ != other.__class__:
            return False

        self_lines = set()
        for line in self:
            line = line.partition('#')[0].strip()
            if line:
                self_lines.add(line)

        other_lines = set()
        for line in other:
            line = line.partition('#')[0].strip()
            if line:
                other_lines.add(line)

        return self_lines == other_lines


class Task(object):
    """ A BNGL task

    Attributes
        model (:obj:`Model`): model
        actions (:obj:`list` of :obj:`str`): actions such as simulations
    """

    def __init__(self, model=None, actions=None):
        self.model = model
        self.actions = actions or []

    def is_equal(self, other):
        """ Determine whether two model blocks are semantically equivalent

        Args:
            other (:obj:`ModelBlock`): second model block

        Returns:
            :obj:`bool`: whether the model blocks are semantically equivalent
        """
        if self.__class__ != other.__class__:
            return False

        if self.model is None:
            if other.model is not None:
                return False
        else:
            if not self.model.is_equal(other.model):
                return False

        if set(self.actions) != set(other.actions):
            return False

        return True


KISAO_SIMULATION_METHOD_ARGUMENTS_MAP = {
    'KISAO_0000019': {
        'id': 'ode',
        'name': 'CVODE',
        'generate_network': True,
        'parameters': {
            'KISAO_0000211': {
                'id': 'atol',
                'name': 'absolute tolerance',
                'type': ValueType.float,
            },
            'KISAO_0000209': {
                'id': 'rtol',
                'name': 'relative tolerance',
                'type': ValueType.float,
            },
            'KISAO_0000525': {
                'id': 'stop_if',
                'name': 'stop condition',
                'type': ValueType.string,
            },
        }
    },
    'KISAO_0000029': {
        'id': 'ssa',
        'name': 'SSA',
        'generate_network': True,
        'parameters': {
            'KISAO_0000488': {
                'id': 'seed',
                'name': 'random number generator seed',
                'type': ValueType.integer,
            },
            'KISAO_0000525': {
                'id': 'stop_if',
                'name': 'stop condition',
                'type': ValueType.string,
            },
        },
    },
    'KISAO_0000263': {
        'id': 'nf',
        'name': 'network free simulation',
        'generate_network': False,
        'parameters': {
            'KISAO_0000488': {
                'id': 'seed',
                'name': 'random number generator seed',
                'type': ValueType.integer,
            },
            'KISAO_0000525': {
                'id': 'stop_if',
                'name': 'stop condition',
                'type': ValueType.string,
            },
        },
    },
    'KISAO_0000524': {
        'id': 'pla',
        'name': 'partitioned leaping method',
        'generate_network': True,
        'parameters': {
            'KISAO_0000488': {
                'id': 'seed',
                'name': 'random number generator seed',
                'type': ValueType.integer,
            },
            'KISAO_0000525': {
                'id': 'stop_if',
                'name': 'stop condition',
                'type': ValueType.string,
            },
        },
    },
}
