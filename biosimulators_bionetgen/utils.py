""" Utilities for working with BioNetGen

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .config import Config
from .data_model import Model, ModelBlock, Task, KISAO_SIMULATION_METHOD_ARGUMENTS_MAP  # noqa: F401
from .io import write_task, read_simulation_results
from biosimulators_utils.report.data_model import VariableResults
from biosimulators_utils.sedml.data_model import (ModelAttributeChange, Variable,  # noqa: F401
                                                  Symbol, UniformTimeCourseSimulation)
from collections import OrderedDict
import os
import pandas  # noqa: F401
import re
import shutil
import subprocess
import tempfile

__all__ = [
    'get_bionetgen_version',
    'add_model_attribute_change_to_task',
    'add_variables_to_model',
    'add_simulation_to_task',
    'exec_bionetgen_task',
    'get_variables_results_from_observable_results',
]


def get_bionetgen_version():
    """ Get the version of BioNetGen

    Returns:
        :obj:`str`: version
    """
    config = Config()
    return subprocess.check_output([config.bionetgen_path, '--version']).decode().strip().split(' ')[2]


def add_model_attribute_change_to_task(task, change):
    """ Encode SED model attribute changes into a BioNetGen task

    * Compartment sizes: targets should follow the pattern ``compartments.<compartment_id>.size``
    * Function expressions: targets should follow the pattern ``functions.<function_id>.expression``
    * Initial species counts: targets should follow the pattern ``species.<species_id>.count``
    * Parameter values: targets should follow the pattern ``parameters.<parameter_id>.value``

    Args:
        task (:obj:`Task`): BioNetGen task
        change (:obj:`ModelAttributeChange`): model attribute change

    Raises:
        :obj:`ValueError`: if a target of a change is not valid
    """
    target = change.target
    new_value = change.new_value

    compartment_size_match = re.match(r'^compartments\.([^\.]+)(\.size)?$', target)
    if compartment_size_match:
        obj_id = compartment_size_match.group(1)
        block = task.model.get('compartments', [])

        pattern = r'^' + re.escape(obj_id) + r' (\d+) ([^ ]+)( .*?)?$'
        comp_changed = False
        for i_line, line in enumerate(block):
            match = re.match(pattern, line)
            if match:
                block[i_line] = '{} {} {} {}'.format(obj_id, match.group(1), new_value, match.group(3) or '').strip()
                comp_changed = True

        if not comp_changed:
            raise ValueError(('The size of compartment `{}` cannot be changed '
                              'because the model does not have a compartment with this id.').format(obj_id))

        return

    parameter_values_match = re.match(r'^parameters\.([^\.]+)(\.value)?$', target)
    if parameter_values_match:
        task.actions.append('setParameter("{}", {})'.format(parameter_values_match.group(1), new_value))
        return

    species_counts_match = re.match(r'^species\.([^\.]+)\((.*?)\)(\.initialCount)?$', target)
    if species_counts_match:
        task.actions.append('setConcentration("{}({})", {})'.format(
            species_counts_match.group(1), species_counts_match.group(2), new_value))
        return

    functions_expression_match = re.match(r'^functions\.([^\.\(\)]+)(\.expression)?$', target)
    if functions_expression_match:
        obj_id = functions_expression_match.group(1)

        block = task.model.get('functions', [])

        func_changed = False
        pattern = r'^' + re.escape(obj_id) + r'\((.*?)\) *= *(.*?)$'
        for i_line, line in enumerate(block):
            match = re.match(pattern, line)
            if match:
                func_changed = True
                block[i_line] = '{}({}) = {}'.format(obj_id, match.group(1), new_value)

        if not func_changed:
            raise ValueError(('The expression of function `{}` cannot be changed '
                              'because the model does not have a function with this id.').format(obj_id))

        return

    function_args_expression_match = re.match(r'^functions\.([^\.]+)\((.*?)\)(\.expression)?$', target)
    if function_args_expression_match:
        obj_id = function_args_expression_match.group(1)
        obj_args = function_args_expression_match.group(2)

        block = task.model.get('functions', [])

        func_changed = False
        pattern = r'^' + re.escape(obj_id) + r'\(.*?\) *= *(.*?)$'
        for i_line, line in enumerate(block):
            match = re.match(pattern, line)
            if match:
                func_changed = True
                block[i_line] = '{}({}) = {}'.format(obj_id, obj_args, new_value)

        if not func_changed:
            raise ValueError(('The expression of function `{}` cannot be changed '
                              'because the model does not have a function with this id.').format(obj_id))

        return

    target_patterns = {
        'compartment size': compartment_size_match,
        'parameter value': parameter_values_match,
        'initial species count/concentration': species_counts_match,
        'function expression': functions_expression_match,
        'function arguments and expression': function_args_expression_match,
    }
    msg = '`{}` is not a valid target. The following patterns of targets are supported:\n  - {}'.format(
        target, '\n  - '.join('{}: `{}`'.format(key, target_patterns[key]) for key in sorted(target_patterns.keys())))
    raise NotImplementedError(msg)


def add_variables_to_model(model, variables):
    """ Encode SED variables into observables in a BioNetGen task

    Args:
        model (:obj:`Model`): model
        variables (:obj:`list` of :obj:`Variable`): desired variables

    Raises:
        :obj:`NotImplementedError`: if BioNetGen doesn't support the symbol or target of a variable
    """
    if not variables:
        return

    observables = model.get('observables', None)
    if observables is None:
        observables = model['observables'] = ModelBlock()
    observables_set = set(observables)

    invalid_symbols = set()
    invalid_targets = set()

    for variable in variables:
        if variable.symbol:
            if variable.symbol != Symbol.time:
                invalid_symbols.add(variable.symbol)

        elif variable.target:
            species_match = re.match(r'^species\.([^\.]+)(\.count)?$', variable.target)
            molecules_match = re.match(r'^molecules\.([^\.]+)(\.count)?$', variable.target)

            if species_match:
                observable = 'Species {} {}'.format(variable.id, species_match.group(1))

            elif molecules_match:
                observable = 'Molecules {} {}'.format(variable.id, molecules_match.group(1))

            if species_match or molecules_match:
                if observable not in observables_set:
                    observables.append(observable)
                    observables_set.add(observable)

            else:
                invalid_targets.add(variable.target)

    if invalid_symbols:
        raise NotImplementedError("".join([
            "The following variable symbols are not supported:\n  - {}\n\n".format(
                '\n  - '.join(sorted(invalid_symbols)),
            ),
            "Symbols must be one of the following:\n  - {}".format(Symbol.time),
        ]))

    if invalid_targets:
        msg = ('The following variable targets are not supported:\n  - {}\n\n'
               'Targets must follow one of the the following patterns:\n  - {}').format(
            '\n  - '.join(sorted(invalid_targets)),
            '\n  - '.join(sorted([
                'species.{ species-id e.g., `A` }.count',
                'molecules.{ molecule-pattern e.g., `A()` }.count',
            ])))
        raise NotImplementedError(msg)


def add_simulation_to_task(task, simulation):
    """ Add a SED simulation to a BioNetGen task

    Args:
        task (:obj:`Task`): BioNetGen task
        simulation (:obj:`UniformTimeCourseSimulation`): SED simulation

    Raises:
        :obj:`NotImplementedError`: if BioNetGen doesn't support the request algorithm or
            algorithm parameters
    """
    simulate_args = OrderedDict()

    # setup the initial time, end time, and the number of time points to record
    simulate_args['t_start'] = simulation.initial_time
    simulate_args['t_end'] = simulation.output_end_time

    n_steps = (
        simulation.number_of_points
        * (simulation.output_end_time - simulation.initial_time)
        / (simulation.output_end_time - simulation.output_start_time)
    )
    if int(n_steps) != n_steps:
        raise NotImplementedError('The simulation must specify an integer number of steps')

    simulate_args['n_steps'] = int(n_steps)

    if simulation.algorithm.kisao_id == 'KISAO_0000263' and simulation.initial_time != 0:
        raise NotImplementedError('The initial time of a network free simulation (KISAO_0000263) must be 0.')

    # setup the simulation method
    algorithm_kisao_id = simulation.algorithm.kisao_id
    simulation_method = KISAO_SIMULATION_METHOD_ARGUMENTS_MAP.get(algorithm_kisao_id, None)
    if not simulation_method:
        raise NotImplementedError("".join([
            "Algorithm with KiSAO id '{}' is not supported. ".format(algorithm_kisao_id),
            "Algorithm must have one of the following KiSAO ids:\n  - {}".format('\n  - '.join(
                '{}: {}'.format(kisao_id, algorithm['name'])
                for kisao_id, algorithm in KISAO_SIMULATION_METHOD_ARGUMENTS_MAP.items())),
        ]))

    simulate_args['method'] = '"{}"'.format(simulation_method['id'])

    # setup the parameters of the simulation algorithm
    for change in simulation.algorithm.changes:
        parameter = simulation_method['parameters'].get(change.kisao_id, None)
        if not parameter:
            raise NotImplementedError("".join([
                "Algorithm parameter with KiSAO id '{}' is not supported. ".format(change.kisao_id),
                "Parameter must have one of the following KiSAO ids:\n  - {}".format('\n  - '.join(
                    '{}: {}'.format(kisao_id, parameter['name']) for kisao_id, parameter in simulation_method['parameters'].items())),
            ]))

        simulate_args[parameter['id']] = change.new_value

    # if necessary add network generation to the BioNetGen task
    if simulation_method['generate_network']:
        task.actions.append("generate_network({overwrite => 1})")

    # add the simulation to the BioNetGen task
    task.actions.append('simulate({{{}}})'.format(', '.join('{} => {}'.format(key, val) for key, val in simulate_args.items())))


def exec_bionetgen_task(task):
    """ Execute a task and return the predicted values of the observables

    Args:
        task (:obj:`Task`): task

    Returns:
        :obj:`pandas.DataFrame`: predicted values of the observables

    Raises:
        :obj:`Exception`: if the task fails
    """

    # create a temporary directory to store the task and its results
    temp_dirname = tempfile.mkdtemp()

    # write the task to a file
    task_filename = os.path.join(temp_dirname, 'task.bngl')
    write_task(task, task_filename)

    # execute the task
    bionetgen_path = Config().bionetgen_path
    try:
        subprocess.check_call([bionetgen_path, task_filename, '--outdir', temp_dirname])
    except Exception:
        # cleanup temporary files
        shutil.rmtree(temp_dirname)
        raise

    # read the predicted observables of the task
    results_filename = os.path.join(temp_dirname, 'task.gdat')
    observable_results = read_simulation_results(results_filename)

    # clean up the temporary directory
    shutil.rmtree(temp_dirname)

    # return the predicted values of the observables of the task
    return observable_results


def get_variables_results_from_observable_results(observable_results, variables):
    """Get the predicted values of the desired variables

    Args:
        observable_results (:obj:`pandas.DataFrame`): predicted values of the observables of a simulation
        variables (:obj:`list` of :obj:`Variable`): desired variables

    Returns:
        :obj:`VariableResults`: predicted values of the desired variables

    Raises:
        :obj:`NotImplementedError`: if an unsupported symbol is requested
        :obj:`ValueError`: if an undefined target is requested
    """
    variable_results = VariableResults()
    invalid_symbols = set()
    invalid_targets = set()
    for variable in variables:
        if variable.symbol:
            if variable.symbol == Symbol.time:
                variable_result = observable_results.loc['time', :]

            else:
                variable_result = None
                invalid_symbols.add(variable.symbol)

        elif variable.target:
            try:
                variable_result = observable_results.loc[variable.id, :]
            except KeyError:
                variable_result = None
                invalid_targets.add(variable.target)

        if variable_result is None:
            variable_results[variable.id] = variable_result
        else:
            variable_results[variable.id] = variable_result.to_numpy()

    if invalid_symbols:
        raise NotImplementedError("".join([
            "The following variable symbols are not supported:\n  - {}\n\n".format(
                '\n  - '.join(sorted(invalid_symbols)),
            ),
            "Symbols must be one of the following:\n  - {}".format(Symbol.time),
        ]))

    if invalid_targets:
        raise ValueError(''.join([
            'The following variable targets could not be recorded:\n  - {}\n\n'.format(
                '\n  - '.join(sorted(invalid_targets)),
            ),
        ]))

    # result results
    return variable_results
