""" BioSimulators-compliant command-line interface to the `BioNetGen <https://bionetgen.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Author: Ali Sinan Saglam <als251@pitt.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .io import read_task
from .utils import (exec_bionetgen_task, preprocess_model_attribute_change, add_model_attribute_change_to_task,
                    create_actions_for_simulation,
                    get_variables_results_from_observable_results, add_variables_to_model)
from .warnings import IgnoredBnglFileContentWarning
from biosimulators_utils.combine.exec import exec_sedml_docs_in_archive
from biosimulators_utils.config import get_config, Config  # noqa: F401
from biosimulators_utils.log.data_model import CombineArchiveLog, TaskLog, StandardOutputErrorCapturerLevel  # noqa: F401
from biosimulators_utils.viz.data_model import VizFormat  # noqa: F401
from biosimulators_utils.report.data_model import ReportFormat, VariableResults, SedDocumentResults  # noqa: F401
from biosimulators_utils.sedml import validation
from biosimulators_utils.sedml.data_model import (Task, ModelLanguage, ModelAttributeChange,  # noqa: F401
                                                  UniformTimeCourseSimulation, Variable)
from biosimulators_utils.sedml.exec import exec_sed_doc as base_exec_sed_doc
from biosimulators_utils.utils.core import raise_errors_warnings
import copy
import warnings

__all__ = ['exec_sedml_docs_in_combine_archive', 'exec_sed_doc', 'exec_sed_task', 'preprocess_sed_task']


def exec_sedml_docs_in_combine_archive(archive_filename, out_dir, config=None):
    """ Execute the SED tasks defined in a COMBINE/OMEX archive and save the outputs

    Args:
        archive_filename (:obj:`str`): path to COMBINE/OMEX archive
        out_dir (:obj:`str`): path to store the outputs of the archive

            * CSV: directory in which to save outputs to files
              ``{ out_dir }/{ relative-path-to-SED-ML-file-within-archive }/{ report.id }.csv``
            * HDF5: directory in which to save a single HDF5 file (``{ out_dir }/reports.h5``),
              with reports at keys ``{ relative-path-to-SED-ML-file-within-archive }/{ report.id }`` within the HDF5 file

        config (:obj:`Config`, optional): BioSimulators common configuration

    Returns:
        :obj:`tuple`:

            * :obj:`SedDocumentResults`: results
            * :obj:`CombineArchiveLog`: log
    """
    return exec_sedml_docs_in_archive(exec_sed_doc, archive_filename, out_dir,
                                      apply_xml_model_changes=False,
                                      config=config)


def exec_sed_doc(doc, working_dir, base_out_path, rel_out_path=None,
                 apply_xml_model_changes=False,
                 log=None, indent=0, pretty_print_modified_xml_models=False,
                 log_level=StandardOutputErrorCapturerLevel.c, config=None):
    """ Execute the tasks specified in a SED document and generate the specified outputs

    Args:
        doc (:obj:`SedDocument` or :obj:`str`): SED document or a path to SED-ML file which defines a SED document
        working_dir (:obj:`str`): working directory of the SED document (path relative to which models are located)

        base_out_path (:obj:`str`): path to store the outputs

            * CSV: directory in which to save outputs to files
              ``{base_out_path}/{rel_out_path}/{report.id}.csv``
            * HDF5: directory in which to save a single HDF5 file (``{base_out_path}/reports.h5``),
              with reports at keys ``{rel_out_path}/{report.id}`` within the HDF5 file

        rel_out_path (:obj:`str`, optional): path relative to :obj:`base_out_path` to store the outputs
        apply_xml_model_changes (:obj:`bool`, optional): if :obj:`True`, apply any model changes specified in the SED-ML file before
            calling :obj:`task_executer`.
        log (:obj:`SedDocumentLog`, optional): log of the document
        indent (:obj:`int`, optional): degree to indent status messages
        pretty_print_modified_xml_models (:obj:`bool`, optional): if :obj:`True`, pretty print modified XML models
        log_level (:obj:`StandardOutputErrorCapturerLevel`, optional): level at which to log output
        config (:obj:`Config`, optional): BioSimulators common configuration
        simulator_config (:obj:`SimulatorConfig`, optional): tellurium configuration

    Returns:
        :obj:`tuple`:

            * :obj:`ReportResults`: results of each report
            * :obj:`SedDocumentLog`: log of the document
    """
    return base_exec_sed_doc(exec_sed_task, doc, working_dir, base_out_path,
                             rel_out_path=rel_out_path,
                             apply_xml_model_changes=apply_xml_model_changes,
                             log=log,
                             indent=indent,
                             pretty_print_modified_xml_models=pretty_print_modified_xml_models,
                             log_level=log_level,
                             config=config)


def exec_sed_task(task, variables, preprocessed_task=None, log=None, config=None):
    """ Execute a task and save its results

    Args:
        task (:obj:`Task`): SED task
        variables (:obj:`list` of :obj:`Variable`): variables that should be recorded
        preprocessed_task (:obj:`dict`, optional): preprocessed information about the task, including possible
            model changes and variables. This can be used to avoid repeatedly executing the same initialization
            for repeated calls to this method.
        log (:obj:`TaskLog`, optional): log for the task
        config (:obj:`Config`, optional): BioSimulators common configuration

    Returns:
        :obj:`tuple`:

            :obj:`VariableResults`: results of variables
            :obj:`TaskLog`: log
    """
    """ Validate task

    * Model is encoded in BNGL
    * Model changes are instances of :obj:`ModelAttributeChange`
    * Simulation is an instance of :obj:`UniformTimeCourseSimulation`

        * Time course is valid
        * initial time <= output start time <= output end time
        * Number of points is an non-negative integer

    Note:

    * Model attribute changes are validated by

        * :obj:`add_model_attribute_change_to_task`
        * BioNetGen

    * Data generator variables are validated by

        * :obj:`add_variables_to_task`
        * BioNetGen
        * :obj:`get_variables_results_from_observable_results`
    """
    config = config or get_config()

    if config.LOG and not log:
        log = TaskLog()

    if preprocessed_task is None:
        preprocessed_task = preprocess_sed_task(task, variables, config=config)

    # read the model from the BNGL file
    bionetgen_task = preprocessed_task['bionetgen_task']
    preprocessed_actions = bionetgen_task.actions
    bionetgen_task.actions = copy.deepcopy(preprocessed_actions)

    # validate and apply the model attribute changes to the BioNetGen task
    for change in task.model.changes:
        add_model_attribute_change_to_task(bionetgen_task, change, preprocessed_task['model_changes'][change.target])

    # apply the SED algorithm and its parameters to the BioNetGen task
    alg_kisao_id = preprocessed_task['algorithm_kisao_id']

    # execute the task
    bionetgen_task.actions.extend(preprocessed_task['simulation_actions'])

    observable_results = exec_bionetgen_task(bionetgen_task)

    # get predicted values of the variables
    variable_results = get_variables_results_from_observable_results(observable_results, variables)
    for key in variable_results.keys():
        variable_results[key] = variable_results[key][-(task.simulation.number_of_points + 1):]

    # log action
    if config.LOG:
        log.algorithm = alg_kisao_id
        log.simulator_details = {
            'actions': bionetgen_task.actions,
        }

    # clean up
    bionetgen_task.actions = preprocessed_actions

    # return the values of the variables and log
    return variable_results, log


def preprocess_sed_task(task, variables, config=None):
    """ Preprocess a SED task, including its possible model changes and variables. This is useful for avoiding
    repeatedly initializing tasks on repeated calls of :obj:`exec_sed_task`.

    Args:
        task (:obj:`Task`): task
        variables (:obj:`list` of :obj:`Variable`): variables that should be recorded
        config (:obj:`Config`, optional): BioSimulators common configuration

    Returns:
        :obj:`dict`: preprocessed information about the task
    """
    config = config or get_config()

    if config.VALIDATE_SEDML:
        raise_errors_warnings(
            validation.validate_task(task),
            error_summary='Task `{}` is invalid.'.format(task.id))
        raise_errors_warnings(
            validation.validate_model_language(task.model.language, ModelLanguage.BNGL),
            error_summary='Language for model `{}` is not supported.'.format(task.model.id))
        raise_errors_warnings(
            validation.validate_model_change_types(task.model.changes, (ModelAttributeChange, )),
            error_summary='Changes for model `{}` are not supported.'.format(task.model.id))
        raise_errors_warnings(
            *validation.validate_model_changes(task.model),
            error_summary='Changes for model `{}` are invalid.'.format(task.model.id))
        raise_errors_warnings(
            validation.validate_simulation_type(task.simulation, (UniformTimeCourseSimulation, )),
            error_summary='{} `{}` is not supported.'.format(
                task.simulation.__class__.__name__,
                task.simulation.id))
        raise_errors_warnings(
            *validation.validate_simulation(task.simulation),
            error_summary='Simulation `{}` is invalid.'.format(task.simulation.id))
        raise_errors_warnings(
            *validation.validate_data_generator_variables(variables),
            error_summary='Data generator variables for task `{}` are invalid.'.format(task.id))

    # read the model from the BNGL file
    bionetgen_task = read_task(task.model.source)
    if bionetgen_task.actions:
        warnings.warn('Actions in the BNGL file were ignored.', IgnoredBnglFileContentWarning)
        bionetgen_task.actions = []

    # validate and apply the model attribute changes to the BioNetGen task
    model_changes = {}
    for change in task.model.changes:
        model_changes[change.target] = preprocess_model_attribute_change(bionetgen_task, change)

    # add observables for the variables to the BioNetGen model
    add_variables_to_model(bionetgen_task.model, variables)

    # apply the SED algorithm and its parameters to the BioNetGen task
    simulation_actions, alg_kisao_id = create_actions_for_simulation(task.simulation)

    # return the values of the variables and log
    return {
        'bionetgen_task': bionetgen_task,
        'model_changes': model_changes,
        'simulation_actions': simulation_actions,
        'algorithm_kisao_id': alg_kisao_id,
    }
