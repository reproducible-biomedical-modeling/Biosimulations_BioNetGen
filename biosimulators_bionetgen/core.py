""" BioSimulators-compliant command-line interface to the `BioNetGen <https://bionetgen.org/>`_ simulation program.

:Author: Jonathan Karr <karr@mssm.edu>
:Author: Ali Sinan Saglam <als251@pitt.edu>
:Date: 2021-01-05
:Copyright: 2020-2021, Center for Reproducible Biomedical Modeling
:License: MIT
"""

from .io import read_task
from .utils import (exec_bionetgen_task, add_model_attribute_change_to_task, add_simulation_to_task,
                    get_variables_results_from_observable_results, add_variables_to_model)
from .warnings import IgnoredBnglFileContentWarning
from biosimulators_utils.combine.exec import exec_sedml_docs_in_archive
from biosimulators_utils.log.data_model import CombineArchiveLog, TaskLog  # noqa: F401
from biosimulators_utils.plot.data_model import PlotFormat  # noqa: F401
from biosimulators_utils.report.data_model import ReportFormat, VariableResults  # noqa: F401
from biosimulators_utils.sedml import validation
from biosimulators_utils.sedml.data_model import (Task, ModelLanguage, ModelAttributeChange,  # noqa: F401
                                                  UniformTimeCourseSimulation, Variable)
from biosimulators_utils.sedml.exec import exec_sed_doc
from biosimulators_utils.utils.core import raise_errors_warnings
import functools
import warnings

__all__ = ['exec_sedml_docs_in_combine_archive', 'exec_sed_task']


def exec_sedml_docs_in_combine_archive(archive_filename, out_dir,
                                       report_formats=None, plot_formats=None,
                                       bundle_outputs=None, keep_individual_outputs=None):
    """ Execute the SED tasks defined in a COMBINE/OMEX archive and save the outputs

    Args:
        archive_filename (:obj:`str`): path to COMBINE/OMEX archive
        out_dir (:obj:`str`): path to store the outputs of the archive

            * CSV: directory in which to save outputs to files
              ``{ out_dir }/{ relative-path-to-SED-ML-file-within-archive }/{ report.id }.csv``
            * HDF5: directory in which to save a single HDF5 file (``{ out_dir }/reports.h5``),
              with reports at keys ``{ relative-path-to-SED-ML-file-within-archive }/{ report.id }`` within the HDF5 file

        report_formats (:obj:`list` of :obj:`ReportFormat`, optional): report format (e.g., csv or h5)
        plot_formats (:obj:`list` of :obj:`PlotFormat`, optional): report format (e.g., pdf)
        bundle_outputs (:obj:`bool`, optional): if :obj:`True`, bundle outputs into archives for reports and plots
        keep_individual_outputs (:obj:`bool`, optional): if :obj:`True`, keep individual output files

    Returns:
        :obj:`CombineArchiveLog`: log
    """
    sed_doc_executer = functools.partial(exec_sed_doc, exec_sed_task)
    return exec_sedml_docs_in_archive(sed_doc_executer, archive_filename, out_dir,
                                      apply_xml_model_changes=False,
                                      report_formats=report_formats,
                                      plot_formats=plot_formats,
                                      bundle_outputs=bundle_outputs,
                                      keep_individual_outputs=keep_individual_outputs)


def exec_sed_task(sed_task, variables, log=None):
    """ Execute a task and save its results

    Args:
       sed_task (:obj:`Task`): task
       variables (:obj:`list` of :obj:`Variable`): variables that should be recorded
       log (:obj:`TaskLog`, optional): log for the task

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
    log = log or TaskLog()

    raise_errors_warnings(validation.validate_task(sed_task),
                          error_summary='Task `{}` is invalid.'.format(sed_task.id))
    raise_errors_warnings(validation.validate_model_language(sed_task.model.language, ModelLanguage.BNGL),
                          error_summary='Language for model `{}` is not supported.'.format(sed_task.model.id))
    raise_errors_warnings(validation.validate_model_change_types(sed_task.model.changes, (ModelAttributeChange, )),
                          error_summary='Changes for model `{}` are not supported.'.format(sed_task.model.id))
    raise_errors_warnings(validation.validate_model_changes(sed_task.model),
                          error_summary='Changes for model `{}` are invalid.'.format(sed_task.model.id))
    raise_errors_warnings(validation.validate_simulation_type(sed_task.simulation, (UniformTimeCourseSimulation, )),
                          error_summary='{} `{}` is not supported.'.format(sed_task.simulation.__class__.__name__, sed_task.simulation.id))
    raise_errors_warnings(validation.validate_simulation(sed_task.simulation),
                          error_summary='Simulation `{}` is invalid.'.format(sed_task.simulation.id))
    raise_errors_warnings(validation.validate_data_generator_variables(variables),
                          error_summary='Data generator variables for task `{}` are invalid.'.format(sed_task.id))

    # read the model from the BNGL file
    bionetgen_task = read_task(sed_task.model.source)
    if bionetgen_task.actions:
        warnings.warn('Actions in the BNGL file were ignored.', IgnoredBnglFileContentWarning)
        bionetgen_task.actions = []

    # validate and apply the model attribute changes to the BioNetGen task
    for change in sed_task.model.changes:
        add_model_attribute_change_to_task(bionetgen_task, change)

    # add observables for the variables to the BioNetGen model
    add_variables_to_model(bionetgen_task.model, variables)

    # apply the SED algorithm and its parameters to the BioNetGen task
    add_simulation_to_task(bionetgen_task, sed_task.simulation)

    # execute the task
    observable_results = exec_bionetgen_task(bionetgen_task)

    # get predicted values of the variables
    variable_results = get_variables_results_from_observable_results(observable_results, variables)
    for key in variable_results.keys():
        variable_results[key] = variable_results[key][-(sed_task.simulation.number_of_points + 1):]

    # log action
    log.algorithm = sed_task.simulation.algorithm.kisao_id
    log.simulator_details = {
        'actions': bionetgen_task.actions,
    }

    # return the values of the variables and log
    return variable_results, log
