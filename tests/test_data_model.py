from biosimulators_bionetgen.data_model import Model, ModelBlock, Task, KISAO_SIMULATION_METHOD_ARGUMENTS_MAP
import json
import os
import unittest


class DataModelTestCase(unittest.TestCase):
    def test_Model(self):
        model = Model()
        model['parameters'] = [
            'k_1 0.0',
            'r_2 0.0',
        ]
        model['molecule types'] = [
            'A()',
            'B()',
            'C()',
        ]
        self.assertEqual(len(model), 2)
        self.assertEqual(len(model['parameters']), 2)
        self.assertEqual(len(model['molecule types']), 3)

    def test_ModelBlock_is_equal(self):
        block_1 = ModelBlock([
            'A', 'B',
        ])
        block_2 = ModelBlock([
            'B', 'A',
        ])
        block_3 = ModelBlock([
            'C', 'A',
        ])
        block_3 = ModelBlock([
            'A', 'B', 'C',
        ])
        block_4 = ModelBlock([
            'A', 'B', '# C',
        ])
        block_5 = [
            'A', 'B',
        ]
        self.assertTrue(block_1.is_equal(block_1))

        self.assertTrue(block_1.is_equal(block_2))
        self.assertFalse(block_1.is_equal(block_3))
        self.assertTrue(block_1.is_equal(block_4))
        self.assertFalse(block_1.is_equal(block_5))

        self.assertTrue(block_2.is_equal(block_1))
        self.assertFalse(block_3.is_equal(block_1))
        self.assertTrue(block_4.is_equal(block_1))

    def test_Block_is_equal(self):
        model_1 = Model()
        model_1['parameters'] = ModelBlock(['A'])
        model_1['molecule types'] = ModelBlock(['A()', 'B()'])

        model_2 = Model()
        model_2['molecule types'] = ModelBlock(['A()', 'B()'])
        model_2['parameters'] = ModelBlock(['A'])

        model_3 = Model()
        model_3['molecule types'] = ModelBlock(['A()', 'B()'])

        model_4 = {}
        model_4['molecule types'] = ModelBlock(['A()', 'B()'])
        model_4['parameters'] = ModelBlock(['A'])

        model_5 = Model()
        model_5['molecule types'] = ModelBlock(['A()', 'C()'])
        model_5['parameters'] = ModelBlock(['A'])

        model_6 = Model()
        model_6['parameters'] = ModelBlock(['A'])
        model_6['molecule types'] = ModelBlock(['A()', 'B()'])
        model_6['reactions'] = ModelBlock([])
        model_6['reactions2'] = ModelBlock([''])
        model_6['reactions3'] = ModelBlock(['#'])

        self.assertTrue(model_1.is_equal(model_1))

        self.assertTrue(model_1.is_equal(model_2))
        self.assertFalse(model_1.is_equal(model_3))
        self.assertFalse(model_1.is_equal(model_4))
        self.assertFalse(model_1.is_equal(model_5))
        self.assertFalse(model_1.is_equal(model_6))

        self.assertTrue(model_2.is_equal(model_1))
        self.assertFalse(model_3.is_equal(model_1))
        self.assertFalse(model_5.is_equal(model_1))
        self.assertFalse(model_6.is_equal(model_1))

    def test_Task_is_equal(self):
        task_1 = Task(model=Model({'parameters': ModelBlock(['A', 'B'])}), actions=['ode', 'nf'])
        task_2 = Task(model=Model({'parameters': ModelBlock(['B', 'A'])}), actions=['nf', 'ode'])
        task_3 = Task(model=Model({'parameters': ModelBlock(['B', 'A', 'C'])}), actions=['nf', 'ode'])
        task_4 = Task(model=Model({'parameters': ModelBlock(['B', 'A'])}), actions=['nf', 'ode', 'ssa'])
        task_5 = Task(model=None, actions=['nf', 'ode'])
        task_6 = Task(model=None, actions=['ode', 'nf'])

        self.assertTrue(task_1.is_equal(task_2))
        self.assertFalse(task_1.is_equal(None))
        self.assertFalse(task_1.is_equal(task_3))
        self.assertFalse(task_1.is_equal(task_4))
        self.assertFalse(task_1.is_equal(task_5))
        self.assertTrue(task_5.is_equal(task_6))

        self.assertTrue(task_2.is_equal(task_1))
        self.assertFalse(task_3.is_equal(task_1))
        self.assertFalse(task_4.is_equal(task_1))
        self.assertFalse(task_5.is_equal(task_1))
        self.assertFalse(task_6.is_equal(task_1))
        self.assertTrue(task_6.is_equal(task_5))

    def test_data_model_matches_specifications(self):
        with open(os.path.join(os.path.dirname(__file__), '..', 'biosimulators.json'), 'r') as file:
            specs = json.load(file)

        self.assertEqual(
            set(KISAO_SIMULATION_METHOD_ARGUMENTS_MAP.keys()),
            set(alg_specs['kisaoId']['id'] for alg_specs in specs['algorithms']))

        for alg_specs in specs['algorithms']:
            alg_props = KISAO_SIMULATION_METHOD_ARGUMENTS_MAP[alg_specs['kisaoId']['id']]

            self.assertEqual(set(alg_props['parameters'].keys()), set(param_specs['kisaoId']['id'] for param_specs in alg_specs['parameters']))

            for param_specs in alg_specs['parameters']:
                param_props = alg_props['parameters'][param_specs['kisaoId']['id']]

                self.assertEqual(param_props['type'], param_specs['type'])
