""" BioSimulators-compliant command-line interface to the `BioNetGen <https://bionetgen.org/>`_ simulation program.

:Author: Ali Sinan Saglam <als251@pitt.edu>
:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-13
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from biosimulations_utils.biomodel.data_model import BiomodelVariable  # noqa: F401
from biosimulators_utils import TimecourseSimulation, TimecourseSimulationexec_sed_tasks_in_combine_archive
import os
import pandas
import re
import shutil
import subprocess
import tempfile

__all__ = ['get_bionetgen_version', 'exec_sedml_docs_in_combine_archive', 'BioNetGenSimulationRunner']


BIONETGEN_PATH = os.getenv(BIONETGEN_PATH, 'BNG2.pl')


def get_bionetgen_version():
    """ Get the version of BioNetGen 

    Returns:
        :obj:`str`: version
    """
    return subprocess.check_output([BIONETGEN_PATH, '--version']).decode().strip().split(' ')[2]


def exec_sedml_docs_in_combine_archive(archive_file, out_dir):
    """ Execute the SED tasks defined in a COMBINE archive and save the outputs

    Args:
        archive_file (:obj:`str`): path to COMBINE archive
        out_dir (:obj:`str`): directory to store the outputs of the tasks
    """
    exec_sed_tasks_in_combine_archive(archive_file, BioNetGenSimulationRunner().run, out_dir)


class BioNetGenSimulationRunner(object):
    def run(self, model_filename, model_sed_urn, simulation, working_dir, out_filename):
        """ Execute a simulation and save its results

        Args:
           model_filename (:obj:`str`): path to the model in BNGL format
           model_sed_urn (:obj:`str`): SED URN for the format of the model (e.g., `urn:sedml:language:sbml`)
           simulation (:obj:`TimecourseSimulation`): simulation
           working_dir (:obj:`str`): directory of the SED-ML file
           out_filename (:obj:`str`): path to save the results of the simulation
        """
        # check that model is encoded in BGNL
        if model_sed_urn != "urn:sedml:language:bngl":
            raise NotImplementedError("Model language with URN '{}' is not supported".format(model_sed_urn))

        # check that simulation is a time course
        if not isinstance(simulation, TimecourseSimulation):
            raise NotImplementedError('{} is not supported'.format(simulation.__class__.__name__))

        # read the model from the BNGL file
        model_lines = self.read_model(model_filename, model_sed_urn)

        # modify the model according to `simulation`
        modified_model_lines = self.modify_model(model_lines, simulation)

        # write the modified model lines to a BNGL file
        fid, modified_model_filename = tempfile.mkstemp(suffix='.bngl')
        os.close(fid)
        with open(modified_model_filename, 'w') as file:
            file.writelines(modified_model_lines)

        # create directory to store results
        out_dir = tempfile.mkdtemp()

        # simulate the modified model
        subprocess.check_call([BIONETGEN_PATH, modified_model_filename, '--outdir', out_dir])

        # put files into output path
        gdat_results_filename = os.path.join(out_dir, os.path.splitext(os.path.basename(modified_model_filename))[0] + '.gdat')
        self.convert_simulation_results(gdat_results_filename, out_filename)

        # cleanup temporary files
        os.remove(modified_model_filename)
        shutil.rmtree(out_dir)

    def read_model(self, model_filename, model_sed_urn):
        """ Read a model from a file

        Args:
           model_filename (:obj:`str`): path to the model in BNGL format
           model_sed_urn (:obj:`str`): SED URN for the format of the model (e.g., `urn:sedml:language:sbml`)

        Returns:
            :obj:`list` of :obj:`str`: model

        Raises:
            :obj:`NotImplementedError`: if the model is not in BGNL format
        """
        with open(model_filename, "r") as file:
            line = file.readline()
            model_lines = []
            # TODO: end model is not necessary, find other
            # ways to check for the action block
            while line.strip() != "end model":
                model_lines.append(line)
                line = file.readline()
            model_lines.append(line)
        return model_lines

    def modify_model(self, model_lines, simulation):
        """ Modify a model according to a specified simulation experiment

        * Modify parameters

            * Compartment sizes: targets should follow the pattern `compartments.<compartment_id>.size`
            * Function expressions: targets should follow the pattern `functions.<function_id>.expression`
            * Initial species counts: targets should follow the pattern `species.<species_id>.count`
            * Parameter values: targets should follow the pattern `parameters.<parameter_id>.value`

        * Set simulation time course
        * Set simulation algorithm and algorithm parameters

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            simulation (:obj:`TimecourseSimulation`): simulation

        Returns:
            :obj:`list` of :obj:`str`: modified model

        Raises:
            :obj:`ValueError`: if a target of a parameter change or the desired simulation algorithm is not valid
        """
        # use `setParameter` to add parameter changes to the model
        for change in simulation.model_parameter_changes:
            target = change.parameter.target.split('.')
            if len(target) != 3:
                raise ValueError("Target must be a tuple of "
                                 "an object type ('compartments', 'functions', 'parameters', or 'species'), "
                                 "object id (e.g., 'A'), and "
                                 "object attribute ('count', 'expression', 'size', or 'value')")

            obj_type, obj_id, obj_attr = target
            if obj_type == 'compartments' and obj_attr == 'size':
                i_block_start, i_block_end = self.find_model_block(model_lines, 'compartments')
                block_lines = self.get_model_block(model_lines, i_block_start, i_block_end)
                comp_changed = False
                for i_line, line in enumerate(block_lines):
                    match = re.match(r'( +)(.*?) +(\d+) +([^ ]+)( +(.*))?$', line)
                    if match and match.group(2).strip() == obj_id:
                        block_lines[i_line] = '{}{} {} {} {}\n'.format(
                            match.group(1), obj_id, match.group(3), change.value, (match.group(5) or '').strip())
                        comp_changed = True
                if not comp_changed:
                    raise ValueError('Model does not have compartment {}'.format(obj_id))
                model_lines = self.replace_model_block(model_lines, i_block_start, i_block_end, block_lines)

            elif obj_type == 'parameters' and obj_attr == 'value':
                model_lines.append('setParameter("{}", {})\n'.format(obj_id, change.value))

            elif obj_type == 'species' and obj_attr == 'count':
                # TODO: is the correct function to use?
                model_lines.append('setConcentration("{}", {})\n'.format(obj_id, change.value))

            elif obj_type == 'functions' and obj_attr == 'expression':
                i_block_start, i_block_end = self.find_model_block(model_lines, 'functions')
                block_lines = self.get_model_block(model_lines, i_block_start, i_block_end)
                func_changed = False
                for i_line, line in enumerate(block_lines):
                    match = re.match(r'( +)(.*?)=(.*?)(#|$)', line)
                    if match and match.group(2).strip() == obj_id:
                        block_lines[i_line] = '{}{} = {}\n'.format(match.group(1), obj_id, change.value)
                        func_changed = True
                if not func_changed:
                    raise ValueError('Model does not have function {}'.format(obj_id))
                model_lines = self.replace_model_block(model_lines, i_block_start, i_block_end, block_lines)

            else:
                raise ValueError('{} of {} cannot be changed'.format(obj_attr, obj_type))

        # get the initial time, end time, and the number of time points to record
        simulate_args = {
            't_start': simulation.start_time,
            't_end': simulation.end_time,
            'n_steps': simulation.num_time_points,
        }

        # validate the simulation algorithm
        if not simulation.algorithm:
            raise ValueError("Simulation must define an algorithm")
        if not simulation.algorithm.kisao_term:
            raise ValueError("Simulation algorithm must include a KiSAO term")
        if simulation.algorithm.kisao_term.ontology != 'KISAO':
            raise ValueError("Simulation algorithm must include a KiSAO term")

        # get the name of the desired simulation algorithm
        if simulation.algorithm.kisao_term.id == '0000019':
            simulate_args['method'] = '"ode"'
        elif simulation.algorithm.kisao_term.id == '0000029':
            simulate_args['method'] = '"ssa"'
        # elif simulation.algorithm.kisao_term.id == 'XXXXXXX':
            # TODO: support PLA once a KISAO term is available
            # simulate_args['method'] = '"pla"'
        elif simulation.algorithm.kisao_term.id == '0000263':
            simulate_args['method'] = '"nf"'
            if simulation.output_start_time:
                simulate_args['equil'] = simulation.output_start_time
        else:
            raise ValueError("Algorithm with KiSAO id {} is not supported".format(simulation.algorithm.kisao_term.id))

        # if necessary add network generation to the model file
        if simulate_args['method'] in ['"ode"', '"ssa"']:
            model_lines.append("generate_network({overwrite => 1})\n")

        # Get the chosen parameters of the chosen simulation algorithm
        alg_params = self.get_algorithm_parameters(simulation.algorithm_parameter_changes)
        for key, val in alg_params.items():
            simulate_args[key] = val

        # add the simulation and the chosen algorithm parameters to the model file
        model_lines.append('simulate({{{}}})\n'.format(', '.join('{} => {}'.format(key, val) for key, val in simulate_args.items())))

        # set desired observables
        model_lines = self.set_observables(model_lines, simulation.model.variables)

        # return the lines for the modified model
        return model_lines

    def get_algorithm_parameters(self, parameter_changes):
        """ Get the desired algorithm parameters for a simulation

        Args:
            parameter_changes (:obj:`list` of :obj:`ParameterChange`): parameter changes

        Returns:
            :obj:`dict`: dictionary that maps the ids of parameters to their values

        Raises:
            :obj:`NotImplementedError`: if desired algorithm parameter is not supported
        """
        bng_parameters = {}
        for change in parameter_changes:
            if change.parameter.kisao_term and change.parameter.kisao_term.ontology == 'KISAO':
                if change.parameter.kisao_term.id == '0000211':
                    # absolute tolerance
                    bng_parameters["atol"] = change.value

                elif change.parameter.kisao_term.id == '0000209':
                    # relative tolerance
                    bng_parameters["rtol"] = change.value

                elif change.parameter.kisao_term.id == '0000488':
                    # relative tolerance
                    bng_parameters["seed"] = change.value

                # if change.parameter.kisao_term.id == 'XXXXXXX':
                    # TODO: support stop_if when KISAO term is available
                    # # stop condition
                    # bng_parameters["stop_if"] = change.value

                else:
                    raise NotImplementedError("Parameter {} is not supported".format(change.parameter.id))

            else:
                raise NotImplementedError("Parameter {} is not supported".format(change.parameter.id))

        return bng_parameters

    def set_observables(self, model_lines, variables):
        """ Set the desired observables of the simulation

        Supports observables of species and molecules

        * Species: variable target should follow the pattern `species.<species_id>.count`
        * Molecules: variable target should follow the pattern `molecules.<molecule_pattern>.count`

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            variables (:obj:`list` of :obj:`BiomodelVariable`): observables to record

        Returns:
            :obj:`list` of :obj:`str`: lines of the modified model

        Raises:
            :obj:`ValueError`: if a target of an observable is not valid
        """
        observables_lines = []
        for var in variables:
            target = var.target.split('.')
            if len(target) != 3:
                raise ValueError("Target must be a tuple of "
                                 "an object type ('molecules', species'), "
                                 "object id (e.g., 'A'), and "
                                 "object attribute ('count')")

            obs_type, obs_id, obs_attr = target
            if obs_type == 'molecules' and obs_attr == 'count':
                observables_lines.append('    Molecules {} {}\n'.format(var.id, obs_id))
            elif obs_type == 'species' and obs_attr == 'count':
                observables_lines.append('    Species {} {}\n'.format(var.id, obs_id))
            else:
                raise ValueError('{} of {} cannot be changed'.format(obs_attr, obs_type))

        i_observables_start, i_observables_end = self.find_model_block(model_lines, 'observables')
        return self.replace_model_block(model_lines, i_observables_start, i_observables_end, observables_lines)

    def find_model_block(self, model_lines, name):
        """ Find the start and end lines of a block of a model

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            name (:obj:`str`): name of the model block (e.g., 'functions', observables', species')

        Returns:
            :obj:`tuple` of :obj:`int`, :obj:`int`: start and end coordinates of the lines of the block
        """
        i_start = None
        i_end = None
        for i_line, line in enumerate(model_lines):
            if re.match(r'^begin +{} *(#|$)'.format(name), line):
                i_start = i_line
            elif re.match(r'^end +{} *(#|$)'.format(name), line):
                i_end = i_line
        return (i_start, i_end)

    def get_model_block(self, model_lines, i_block_start, i_block_end):
        """ Replace a block of a model

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            i_block_start (:obj:`int`): start line of the block within :obj:`model_lines`
            i_block_end (:obj:`int`): end line of the block within :obj:`model_lines`

        Returns:
            :obj:`list` of :obj:`str`: lines of the block
        """
        return model_lines[i_block_start + 1:i_block_end]

    def replace_model_block(self, model_lines, i_old_block_start, i_old_block_end, new_block_lines):
        """ Replace a block of a model

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            i_old_block_start (:obj:`int`): start line of the block within :obj:`model_lines`
            i_old_block_end (:obj:`int`): end line of the block within :obj:`model_lines`
            new_block_lines (:obj:`list` of :obj:`str`): new lines of the block

        Returns:
            :obj:`list` of :obj:`str`: lines of the modified model
        """
        return model_lines[0:i_old_block_start + 1] \
            + new_block_lines \
            + model_lines[i_old_block_end:]

    def convert_simulation_results(self, gdat_filename, out_filename):
        """ Convert simulation results from gdat to the desired output format

        Args:
            gdat_filename (:obj:`str`): path to simulation results in gdat format
            out_filename (:obj:`str`): path to save the results of the simulation

        Raises:
            :obj:`NotImplementedError`: if the desired output format is not supported
        """
        data = self.read_simulation_results(gdat_filename)

    def read_simulation_results(self, gdat_filename):
        """ Read the results of a simulation

        Args:
            gdat_filename (:obj:`str`): path to simulation results in gdat format

        Returns:
            :obj:`pandas.DataFrame`: simulation results
        """
        with open(gdat_filename, "r") as file:
            # Get column names from first line of file
            line = file.readline()
            names = re.split(r'\s+', (re.sub('#', '', line)).strip())

            # Read results
            results = pandas.read_table(file, sep=r'\s+', header=None, names=names)

        # Set the time as index
        results = results.set_index("time")

        # Return results
        return results
