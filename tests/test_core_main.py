""" Tests of the BioNetGen command-line interface and Docker image

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""


from biosimulators_bionetgen import __main__
from biosimulators_bionetgen.core import exec_sed_task, exec_sedml_docs_in_combine_archive
from biosimulators_utils.combine import data_model as combine_data_model
from biosimulators_utils.combine.io import CombineArchiveWriter
from biosimulators_utils.config import get_config
from biosimulators_utils.report import data_model as report_data_model
from biosimulators_utils.report.io import ReportReader
from biosimulators_utils.sedml import data_model as sedml_data_model
from biosimulators_utils.sedml.io import SedmlSimulationWriter
from biosimulators_utils.sedml.utils import append_all_nested_children_to_doc
from biosimulators_utils.simulator.exec import exec_sedml_docs_in_archive_with_containerized_simulator
from biosimulators_utils.simulator.specs import gen_algorithms_from_specs
from unittest import mock
import copy
import datetime
import dateutil.tz
import numpy
import os
import shutil
import tempfile
import unittest


class CliTestCase(unittest.TestCase):
    DOCKER_IMAGE = 'ghcr.io/biosimulators/biosimulators_bionetgen/bionetgen:latest'

    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_exec_sed_task(self):
        doc = self._build_sed_doc()
        doc.models[0].source = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')

        variables = [data_gen.variables[0] for data_gen in doc.data_generators]
        variable_results, _ = exec_sed_task(doc.tasks[0], variables)

        self.assertEqual(set(variable_results.keys()), set([var.id for var in variables]))
        for var in variables:
            self.assertFalse(numpy.any(numpy.isnan(variable_results[var.id])))
        sim = doc.tasks[0].simulation
        self.assertEqual(variable_results['var_time'].size, sim.number_of_points + 1)
        numpy.testing.assert_allclose(variable_results['var_time'],
                                      numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1))
        numpy.testing.assert_allclose(variable_results['var_A'][0], 4, rtol=1e-1)

        doc2 = copy.deepcopy(doc)
        doc2.tasks[0].model.changes.append(sedml_data_model.ModelAttributeChange(
            target='species.A().initialCount',
            new_value='5',
        ))
        variable_results_2, _ = exec_sed_task(doc2.tasks[0], variables)
        numpy.testing.assert_allclose(variable_results_2['var_A'][0], 5, rtol=1e-1)
        self.assertGreater(variable_results_2['var_A'][0], variable_results['var_A'][0])

        doc3 = copy.deepcopy(doc)
        doc3.tasks[0].model.changes.append(sedml_data_model.ModelAttributeChange(
            target='species.A().initialCount',
            new_value=6,
        ))
        variable_results_3, _ = exec_sed_task(doc3.tasks[0], variables)
        numpy.testing.assert_allclose(variable_results_3['var_A'][0], 6, rtol=1e-1)
        self.assertGreater(variable_results_3['var_A'][0], variable_results_2['var_A'][0])

    def test_exec_sed_task_positive_initial_time(self):
        doc = self._build_sed_doc()
        doc.models[0].source = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        doc.simulations[0].initial_time = 0.1

        variables = [data_gen.variables[0] for data_gen in doc.data_generators]
        variable_results, _ = exec_sed_task(doc.tasks[0], variables)

        self.assertEqual(set(variable_results.keys()), set([var.id for var in variables]))
        for var in variables:
            self.assertFalse(numpy.any(numpy.isnan(variable_results[var.id])))
        sim = doc.tasks[0].simulation
        self.assertEqual(variable_results['var_time'].size, sim.number_of_points + 1)
        numpy.testing.assert_allclose(variable_results['var_time'],
                                      numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1))

    def test_exec_sed_task_negative_initial_time(self):
        doc = self._build_sed_doc()
        doc.models[0].source = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        doc.simulations[0].initial_time = -0.1
        doc.simulations[0].output_start_time = -0.1
        doc.simulations[0].output_end_time = 19.9
        doc.simulations[0].number_of_points = 20

        variables = [data_gen.variables[0] for data_gen in doc.data_generators]
        variable_results, _ = exec_sed_task(doc.tasks[0], variables)

        self.assertEqual(set(variable_results.keys()), set([var.id for var in variables]))
        for var in variables:
            self.assertFalse(numpy.any(numpy.isnan(variable_results[var.id])))
        sim = doc.tasks[0].simulation
        self.assertEqual(variable_results['var_time'].size, sim.number_of_points + 1)
        numpy.testing.assert_allclose(variable_results['var_time'],
                                      numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1))

    def test_exec_sed_task_output_step_interval(self):
        doc = self._build_sed_doc()
        doc.models[0].source = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        sim = doc.simulations[0]
        sim.initial_time = 0.
        sim.output_start_time = 0.
        sim.output_end_time = 0.1
        sim.number_of_points = 10
        sim.algorithm.changes.append(
            sedml_data_model.AlgorithmParameterChange(kisao_id='KISAO_0000684', new_value='2'),
        )
        sim.algorithm.changes.append(
            sedml_data_model.AlgorithmParameterChange(kisao_id='KISAO_0000415', new_value='1000000'),
        )

        variables = [data_gen.variables[0] for data_gen in doc.data_generators]
        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'NONE'}):
            with self.assertRaises(NotImplementedError):
                exec_sed_task(doc.tasks[0], variables)

        with mock.patch.dict('os.environ', {'ALGORITHM_SUBSTITUTION_POLICY': 'SIMILAR_VARIABLES'}):
            results, _ = exec_sed_task(doc.tasks[0], variables)

        numpy.testing.assert_allclose(results['var_time'],
                                      numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1))

    def test_exec_sedml_docs_in_combine_archive(self):
        doc, archive_filename = self._build_combine_archive()

        out_dir = os.path.join(self.dirname, 'out')

        config = get_config()
        config.REPORT_FORMATS = [report_data_model.ReportFormat.h5, report_data_model.ReportFormat.csv]
        config.BUNDLE_OUTPUTS = True
        config.KEEP_INDIVIDUAL_OUTPUTS = True

        _, log = exec_sedml_docs_in_combine_archive(archive_filename, out_dir, config=config)
        if log.exception:
            raise log.exception

        self._assert_combine_archive_outputs(doc, out_dir)

    def test_exec_sedml_docs_in_combine_archive_with_all_algorithms(self):
        for alg in gen_algorithms_from_specs(os.path.join(os.path.dirname(__file__), '..', 'biosimulators.json')).values():
            doc, archive_filename = self._build_combine_archive(algorithm=alg)

            out_dir = os.path.join(self.dirname, alg.kisao_id)

            config = get_config()
            config.REPORT_FORMATS = [report_data_model.ReportFormat.h5, report_data_model.ReportFormat.csv]
            config.BUNDLE_OUTPUTS = True
            config.KEEP_INDIVIDUAL_OUTPUTS = True

            _, log = exec_sedml_docs_in_combine_archive(archive_filename, out_dir, config=config)
            if log.exception:
                raise log.exception
            self._assert_combine_archive_outputs(doc, out_dir)

    def test_exec_with_cli(self):
        doc, archive_filename = self._build_combine_archive()

        out_dir = os.path.join(self.dirname, 'out')
        with mock.patch.dict(os.environ, self._get_combine_archive_exec_env()):
            with __main__.App(argv=['-i', archive_filename, '-o', out_dir]) as app:
                app.run()

        self._assert_combine_archive_outputs(doc, out_dir)

    def test_exec_with_docker_image(self):
        doc, archive_filename = self._build_combine_archive()

        out_dir = os.path.join(self.dirname, 'out')

        env = self._get_combine_archive_exec_env()
        exec_sedml_docs_in_archive_with_containerized_simulator(
            archive_filename, out_dir, self.DOCKER_IMAGE, environment=env, pull_docker_image=False)

        self._assert_combine_archive_outputs(doc, out_dir)

    def _build_combine_archive(self, algorithm=None):
        doc = self._build_sed_doc(algorithm=algorithm)

        archive_dirname = os.path.join(self.dirname, 'archive')
        if not os.path.isdir(archive_dirname):
            os.mkdir(archive_dirname)

        model_filename = os.path.join(archive_dirname, 'model_1.bngl')
        shutil.copyfile(
            os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl'),
            model_filename)

        sim_filename = os.path.join(archive_dirname, 'sim_1.sedml')
        SedmlSimulationWriter().run(doc, sim_filename)

        archive = combine_data_model.CombineArchive(
            contents=[
                combine_data_model.CombineArchiveContent(
                    'model_1.bngl', combine_data_model.CombineArchiveContentFormat.BNGL.value),
                combine_data_model.CombineArchiveContent(
                    'sim_1.sedml', combine_data_model.CombineArchiveContentFormat.SED_ML.value),
            ],
        )
        archive_filename = os.path.join(self.dirname,
                                        'archive.omex' if algorithm is None else 'archive-{}.omex'.format(algorithm.kisao_id))
        CombineArchiveWriter().run(archive, archive_dirname, archive_filename)

        return (doc, archive_filename)

    def _build_sed_doc(self, algorithm=None):
        if algorithm is None:
            algorithm = sedml_data_model.Algorithm(
                kisao_id='KISAO_0000019',
                changes=[
                    sedml_data_model.AlgorithmParameterChange(
                        kisao_id='KISAO_0000211',
                        new_value='2e-8',
                    ),
                ],
            )

        doc = sedml_data_model.SedDocument()
        doc.models.append(sedml_data_model.Model(
            id='model_1',
            source='model_1.bngl',
            language=sedml_data_model.ModelLanguage.BNGL.value,
            changes=[
                sedml_data_model.ModelAttributeChange(target='functions.gfunc.expression', new_value='0.5*Atot^2/(10 + Atot^2)'),
                sedml_data_model.ModelAttributeChange(target='functions.gfunc().expression', new_value='0.5*Atot^2/(10 + Atot^2)'),
                sedml_data_model.ModelAttributeChange(target='species.A().initialCount', new_value='4'),
                sedml_data_model.ModelAttributeChange(target='parameters.g1.value', new_value='18.0'),
            ],
        ))
        doc.simulations.append(sedml_data_model.UniformTimeCourseSimulation(
            id='sim_1_time_course',
            algorithm=algorithm,
            initial_time=0.,
            output_start_time=0.1,
            output_end_time=0.2,
            number_of_points=20,
        ))
        doc.tasks.append(sedml_data_model.Task(
            id='task_1',
            model=doc.models[0],
            simulation=doc.simulations[0],
        ))
        doc.data_generators.append(sedml_data_model.DataGenerator(
            id='data_gen_time',
            variables=[
                sedml_data_model.Variable(
                    id='var_time',
                    symbol=sedml_data_model.Symbol.time,
                    task=doc.tasks[0],
                ),
            ],
            math='var_time',
        ))
        doc.data_generators.append(sedml_data_model.DataGenerator(
            id='data_gen_A',
            variables=[
                sedml_data_model.Variable(
                    id='var_A',
                    target="species.A",
                    task=doc.tasks[0],
                ),
            ],
            math='var_A',
        ))
        doc.data_generators.append(sedml_data_model.DataGenerator(
            id='data_gen_B',
            variables=[
                sedml_data_model.Variable(
                    id='var_B',
                    target='species.B.count',
                    task=doc.tasks[0],
                ),
            ],
            math='var_B',
        ))
        doc.data_generators.append(sedml_data_model.DataGenerator(
            id='data_gen_GeneA_00',
            variables=[
                sedml_data_model.Variable(
                    id='var_GeneA_00',
                    target="molecules.GeneA_00()",
                    task=doc.tasks[0],
                ),
            ],
            math='var_GeneA_00',
        ))
        doc.data_generators.append(sedml_data_model.DataGenerator(
            id='data_gen_GeneA_01',
            variables=[
                sedml_data_model.Variable(
                    id='var_GeneA_01',
                    target="molecules.GeneA_01()",
                    task=doc.tasks[0],
                ),
            ],
            math='var_GeneA_01',
        ))
        doc.outputs.append(sedml_data_model.Report(
            id='report_1',
            data_sets=[
                sedml_data_model.DataSet(id='data_set_time', label='Time', data_generator=doc.data_generators[0]),
                sedml_data_model.DataSet(id='data_set_A', label='A', data_generator=doc.data_generators[1]),
                sedml_data_model.DataSet(id='data_set_B', label='B', data_generator=doc.data_generators[2]),
                sedml_data_model.DataSet(id='data_set_GeneA_00', label='GeneA_00', data_generator=doc.data_generators[3]),
                sedml_data_model.DataSet(id='data_set_GeneA_01', label='GeneA_01', data_generator=doc.data_generators[4]),
            ],
        ))

        append_all_nested_children_to_doc(doc)

        return doc

    def _get_combine_archive_exec_env(self):
        return {
            'REPORT_FORMATS': 'h5,csv'
        }

    def _assert_combine_archive_outputs(self, doc, out_dir):
        self.assertEqual(set(['reports.h5', 'reports.zip', 'sim_1.sedml']).difference(set(os.listdir(out_dir))), set())

        # check HDF report
        report = doc.outputs[0]
        report_results = ReportReader().run(report, out_dir, 'sim_1.sedml/report_1', format=report_data_model.ReportFormat.h5)

        self.assertEqual(sorted(report_results.keys()), sorted([d.id for d in report.data_sets]))

        sim = doc.tasks[0].simulation
        self.assertEqual(len(report_results[report.data_sets[0].id]), sim.number_of_points + 1)
        numpy.testing.assert_almost_equal(
            report_results[report.data_sets[0].id],
            numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1),
        )

        for data_set_result in report_results.values():
            self.assertFalse(numpy.any(numpy.isnan(data_set_result)))

        # check CSV report
        report_results = ReportReader().run(report, out_dir, 'sim_1.sedml/report_1', format=report_data_model.ReportFormat.csv)

        self.assertEqual(sorted(report_results.keys()), sorted([d.id for d in report.data_sets]))

        sim = doc.tasks[0].simulation
        self.assertEqual(len(report_results[report.data_sets[0].id]), sim.number_of_points + 1)
        numpy.testing.assert_almost_equal(
            report_results[report.data_sets[0].id],
            numpy.linspace(sim.output_start_time, sim.output_end_time, sim.number_of_points + 1),
        )

        for data_set_result in report_results.values():
            self.assertFalse(numpy.any(numpy.isnan(data_set_result)))

    def test_raw_cli(self):
        with mock.patch('sys.argv', ['', '--help']):
            with self.assertRaises(SystemExit) as context:
                __main__.main()
                self.assertRegex(context.Exception, 'usage: ')
