from biosimulators_bionetgen.config import Config
from biosimulators_bionetgen.data_model import Task
from biosimulators_bionetgen.utils import (get_bionetgen_version,
                                           add_model_attribute_change_to_task,
                                           add_variables_to_model,
                                           add_simulation_to_task,
                                           exec_bionetgen_task,
                                           get_variables_results_from_observable_results)
from biosimulators_bionetgen.io import read_task, read_simulation_results
from biosimulators_utils.sedml.data_model import (ModelAttributeChange, DataGeneratorVariable,
                                                  DataGeneratorVariableSymbol, UniformTimeCourseSimulation,
                                                  Algorithm, AlgorithmParameterChange)
from unittest import mock
import os
import numpy
import numpy.testing
import shutil
import subprocess
import tempfile
import unittest


class UtilsTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_get_bionetgen_version(self):
        self.assertRegex(get_bionetgen_version(), r'^\d+\.\d+\.\d+$')

    def test_add_model_attribute_change_to_task(self):
        model_filename = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')

        task = read_task(model_filename)
        task.model['compartments'] = [
            'EC 3 vol_EC',
            'PM 2 sa_PM*eff_width EC',
        ]
        change = ModelAttributeChange(target='compartments.EC.size', new_value='0.5')
        add_model_attribute_change_to_task(task, change)
        self.assertEqual(task.model['compartments'], [
            'EC 3 0.5',
            'PM 2 sa_PM*eff_width EC',
        ])

        task = read_task(model_filename)
        change = ModelAttributeChange(target='functions.gfunc().expression', new_value='0.5')
        add_model_attribute_change_to_task(task, change)
        self.assertEqual(task.model['functions'], ['gfunc() = 0.5'])

        task = read_task(model_filename)
        change = ModelAttributeChange(target='functions.gfunc.expression', new_value='0.5')
        add_model_attribute_change_to_task(task, change)
        self.assertEqual(task.model['functions'], ['gfunc() = 0.5'])

        change = ModelAttributeChange(target='parameters.k_1.value', new_value='1.0')
        add_model_attribute_change_to_task(task, change)
        self.assertEqual(task.actions[-1], 'setParameter("k_1", 1.0)')

        change = ModelAttributeChange(target='species.GeneA_00().initialCount', new_value='1')
        add_model_attribute_change_to_task(task, change)
        self.assertEqual(task.actions[-1], 'setConcentration("GeneA_00()", 1)')

        # error: no compartment
        task = read_task(model_filename)
        task.model['compartments'] = [
            'EC 3 vol_EC',
            'PM 2 sa_PM*eff_width EC',
        ]
        change = ModelAttributeChange(target='compartments.CE.size', new_value='0.5')
        with self.assertRaisesRegex(ValueError, 'the model does not have a compartment'):
            add_model_attribute_change_to_task(task, change)

        # error: no function
        change = ModelAttributeChange(target='functions.hfunc.expression', new_value='0.5')
        with self.assertRaisesRegex(ValueError, 'the model does not have a function'):
            add_model_attribute_change_to_task(task, change)

        # error: no function
        change = ModelAttributeChange(target='functions.hfunc().expression', new_value='0.5')
        with self.assertRaisesRegex(ValueError, 'the model does not have a function'):
            add_model_attribute_change_to_task(task, change)

        # error: no function
        change = ModelAttributeChange(target='section.object.attribute', new_value='0.5')
        with self.assertRaisesRegex(NotImplementedError, 'is not a valid target'):
            add_model_attribute_change_to_task(task, change)

    def test_add_variables_to_task(self):
        model_filename = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        task = read_task(model_filename)
        task.model.pop('observables')

        variables = [
            DataGeneratorVariable(id='Time', symbol=DataGeneratorVariableSymbol.time),
            DataGeneratorVariable(id='A', target='species.A'),
            DataGeneratorVariable(id='B', target='species.B.count'),
            DataGeneratorVariable(id='Atot', target='molecules.A()'),
            DataGeneratorVariable(id='GA00tot', target='molecules.GeneA_00().count'),
        ]
        add_variables_to_model(task.model, variables)

        self.assertEqual(task.model['observables'], [
            'Species A A',
            'Species B B',
            'Molecules Atot A()',
            'Molecules GA00tot GeneA_00()',
        ])

        task.model.move_to_end('functions')
        task.model.move_to_end('reaction rules')
        results = exec_bionetgen_task(task)

        self.assertEqual(set(results.index), set([
            'time',
            'A',
            'B',
            'Atot',
            'GA00tot',
        ]))

        add_variables_to_model(task.model, [])
        self.assertEqual(task.model['observables'], [
            'Species A A',
            'Species B B',
            'Molecules Atot A()',
            'Molecules GA00tot GeneA_00()',
        ])

        # error handling
        with self.assertRaisesRegex(NotImplementedError, 'symbols are not supported'):
            add_variables_to_model(task.model, [DataGeneratorVariable(id='X', symbol='x')])

        with self.assertRaisesRegex(NotImplementedError, 'targets are not supported'):
            add_variables_to_model(task.model, [DataGeneratorVariable(id='X', target='x')])

    def test_add_simulation_to_task(self):
        # CVODE
        task = Task()
        simulation = UniformTimeCourseSimulation(
            initial_time=0.,
            output_start_time=10.,
            output_end_time=20.,
            number_of_points=10,
            algorithm=Algorithm(
                kisao_id='KISAO_0000019',
                changes=[
                    AlgorithmParameterChange(kisao_id='KISAO_0000211', new_value='1e-6'),
                ]
            ),
        )
        add_simulation_to_task(task, simulation)
        self.assertEqual(task.actions, [
            'generate_network({overwrite => 1})',
            'simulate({t_start => 0.0, t_end => 20.0, n_steps => 20, method => "ode", atol => 1e-6})',
        ])

        # Error handling: non-integer steps
        simulation.output_end_time = 20.1
        with self.assertRaisesRegex(NotImplementedError, 'must specify an integer number of steps'):
            add_simulation_to_task(task, simulation)

        # Error handling: unknown algorithm
        simulation.output_end_time = 20.0
        simulation.algorithm.kisao_id = 'KISAO_0000001'
        with self.assertRaisesRegex(NotImplementedError, 'is not supported. Algorithm must have'):
            add_simulation_to_task(task, simulation)

        # Error handling: unknown algorithm parameter
        simulation.algorithm.kisao_id = 'KISAO_0000019'
        simulation.algorithm.changes[0].kisao_id = 'KISAO_0000001'
        with self.assertRaisesRegex(NotImplementedError, 'is not supported. Parameter must have'):
            add_simulation_to_task(task, simulation)

    def test_exec_bionetgen_task(self):
        model_filename = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        task = read_task(model_filename)

        results = exec_bionetgen_task(task)

        self.assertEqual(set(results.index), set([
            'time',
            'Atot',
            'Btot',
            'GA00tot',
            'GA01tot',
            'GA10tot',
            'GB00tot',
            'GB01tot',
            'GB10tot',
        ]))

        self.assertFalse(numpy.any(numpy.isnan(results)))
        numpy.testing.assert_allclose(results.loc['time', :], numpy.linspace(0., 1000000., 1000 + 1))

        # error handling
        with mock.patch('subprocess.check_call', side_effect=ValueError('big error')):
            with self.assertRaisesRegex(ValueError, 'big error'):
                exec_bionetgen_task(task)

    def test_get_variables_results_from_observable_results(self):
        bionetgen_path = Config().bionetgen_path
        model_filename = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        subprocess.check_call([bionetgen_path, model_filename, '--outdir', self.dirname])

        obs_results = read_simulation_results(os.path.join(self.dirname, 'test.gdat'))
        variables = [
            DataGeneratorVariable(id='Time', symbol=DataGeneratorVariableSymbol.time),
            DataGeneratorVariable(id='Atot', target='A()'),
            DataGeneratorVariable(id='GA00tot', target='GeneA_00()'),
        ]
        var_results = get_variables_results_from_observable_results(obs_results, variables)

        self.assertEqual(set(var_results.keys()), set([
            'Time',
            'Atot',
            'GA00tot',
        ]))

        for values in var_results.values():
            self.assertFalse(numpy.any(numpy.isnan(values)))
        numpy.testing.assert_allclose(var_results['Time'], numpy.linspace(0., 1000000., 1000 + 1))

        # handle errors
        variables.append(DataGeneratorVariable(id='X', symbol='x'))
        with self.assertRaisesRegex(NotImplementedError, 'symbols are not supported'):
            get_variables_results_from_observable_results(obs_results, variables)

        variables[-1].symbol = None
        variables[-1].target = 'undefined'
        with self.assertRaisesRegex(ValueError, 'could not be recorded'):
            get_variables_results_from_observable_results(obs_results, variables)
