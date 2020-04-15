""" BioSimulations-compliant command-line interface to the `BioNetGen <https://bionetgen.org/>`_ simulation program.

:Author: Ali Sinan Saglam <als251@pitt.edu>
:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-13
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from Biosimulations_utils.biomodel.data_model import BiomodelVariable  # noqa: F401
from Biosimulations_utils.simulation.data_model import Simulation  # noqa: F401
from Biosimulations_utils.simulator.utils import exec_simulations_in_archive
import os
import pandas
import re
import shutil
import subprocess
import tempfile

__all__ = ['exec_combine_archive', 'BioNetGenSimulationRunner']


def exec_combine_archive(archive_file, out_dir):
    """ Execute the SED tasks defined in a COMBINE archive and save the outputs

    Args:
        archive_file (:obj:`str`): path to COMBINE archive
        out_dir (:obj:`str`): directory to store the outputs of the tasks
    """
    exec_simulations_in_archive(archive_file, BioNetGenSimulationRunner().run, out_dir)


class BioNetGenSimulationRunner(object):
    def run(self, model_filename, model_sed_urn, simulation, working_dir, out_filename, out_format):
        """ Execute a simulation and save its results

        Args:
           model_filename (:obj:`str`): path to the model in BNGL format
           model_sed_urn (:obj:`str`): SED URN for the format of the model (e.g., `urn:sedml:language:sbml`)
           simulation (:obj:`Simulation`): simulation
           working_dir (:obj:`str`): directory of the SED-ML file
           out_filename (:obj:`str`): path to save the results of the simulation
           out_format (:obj:`str`): format to save the results of the simulation (e.g., `csv`)
        """

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
        subprocess.call(['BNG2.pl', modified_model_filename, '--outdir', out_dir])

        # put files into output path
        gdat_results_filename = os.path.join(out_dir, os.path.splitext(os.path.basename(modified_model_filename))[0] + '.gdat')
        self.convert_simulation_results(gdat_results_filename, out_filename, out_format)

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
        if model_sed_urn != 'urn:sedml:language:bngl':
            raise NotImplementedError('Model format with SED URN {} is not supported'.format(model_sed_urn))

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

        * Modify model parameters
        * Set simulation time course
        * Set simulation algorithm and algorithm parameters

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            simulation (:obj:`Simulation`): simulation

        Returns:
            :obj:`list` of :obj:`str`: modified model

        Raises:
            :obj:`NotImplementedError`: if the desired simulation algorithm is not supported
        """

        # use `setParameter` to add parameter changes to the model
        for change in simulation.model_parameter_changes:
            # TODO: review the address scheme and BNGL methods
            param_type, _, param_id = change.parameter.target.partition('.')
            if param_type == 'parameters':
                model_lines.append('setParameter("{}", {})\n'.format(param_id, change.value))
            elif param_type == 'species':
                model_lines.append('setConcentration("{}", {})\n'.format(param_id, change.value))

        # get the initial time, end time, and the number of time points to record
        simulate_args = {
            't_start': simulation.start_time,
            't_end': simulation.end_time,
            'n_steps': simulation.num_time_points,
        }

        # validate the simulation algorithm
        assert simulation.algorithm, "Simulation must define an algorithm"
        assert simulation.algorithm.kisao_term, "Simulation algorithm must include a KiSAO term"
        assert simulation.algorithm.kisao_term.ontology == 'KISAO', "Simulation algorithm must include a KiSAO term"

        # get the name of the desired simulation algorithm
        # TODO: support PLA
        if simulation.algorithm.kisao_term.id == '0000019':
            simulate_args['method'] = '"ode"'
        elif simulation.algorithm.kisao_term.id == '0000029':
            simulate_args['method'] = '"ssa"'
        elif simulation.algorithm.kisao_term.id == '0000263':
            simulate_args['method'] = '"nf"'
            if simulation.output_start_time:
                simulate_args['equil'] = simulation.output_start_time
        else:
            raise NotImplementedError("Algorithm with KiSAO id {} is not supported".format(simulation.algorithm.kisao_term.id))

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
        # TODO: support additional parameters:
        # - stop_if
        # - ode
        #   - sparse
        #   - steady_state
        # - nf
        #   - complex: true
        #   - nocslf: false
        #   - notf: false
        #   - gml: 100000
        #   - additional params?
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

                else:
                    raise NotImplementedError("Parameter {} is not supported".format(change.parameter.id))

            else:
                raise NotImplementedError("Parameter {} is not supported".format(change.parameter.id))

        return bng_parameters

    def set_observables(self, model_lines, variables):
        """ Set the desired observables of the simulation

        Args:
            model_lines (:obj:`list` of :obj:`str`): lines of the model
            variables (:obj:`list` of :obj:`BiomodelVariable`): observables to record

        Returns:
            :obj:`list` of :obj:`str`: lines of the modified model
        """
        i_observables_start = None
        i_observables_end = None
        for i_line, line in enumerate(model_lines):
            if re.match(r'^begin +observables *(#|$)', line):
                i_observables_start = i_line
            elif re.match(r'^end +observables *(#|$)', line):
                i_observables_end = i_line

        observables_lines = []
        for var in variables:
            # TODO: review
            molecule_type, _, molecule_id = var.target.partition('.')
            assert molecule_type == 'molecules', "Variable target must be a molecule"
            observables_lines.append('Molecules {} {}\n'.format(var.id, molecule_id))

        modified_model_lines = \
            model_lines[0:i_observables_start + 1] \
            + observables_lines \
            + model_lines[i_observables_end:]

        return modified_model_lines

    def convert_simulation_results(self, gdat_filename, out_filename, out_format):
        """ Convert simulation results from gdat to the desired output format

        Args:
            gdat_filename (:obj:`str`): path to simulation results in gdat format
            out_filename (:obj:`str`): path to save the results of the simulation
            out_format (:obj:`str`): format to save the results of the simulation (e.g., `csv`)

        Raises:
            :obj:`NotImplementedError`: if the desired output format is not supported
        """
        data = self.read_simulation_results(gdat_filename)
        if out_format == 'csv':
            data.to_csv(out_filename)
        elif out_format == 'tsv':
            data.to_csv(out_filename, sep='\t')
        else:
            raise NotImplementedError('Unsupported output format {}'.format(out_format))

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
