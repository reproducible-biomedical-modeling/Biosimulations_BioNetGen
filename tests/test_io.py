from biosimulators_bionetgen.config import Config
from biosimulators_bionetgen.data_model import Task, Model, ModelBlock
from biosimulators_bionetgen.io import write_task, read_task, read_simulation_results
from biosimulators_bionetgen.warnings import IgnoredBnglFileContentWarning
import numpy
import numpy.testing
import os
import pytest
import shutil
import subprocess
import tempfile
import unittest


class DataModelTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_write_task(self):
        task = Task()
        model = task.model = Model()
        model['parameters'] = ModelBlock([
            'k_1 0.0',
            'r_2 0.0',
        ])
        model['molecule types'] = ModelBlock([
            'A()',
            'B()',
            'C()',
        ])
        task.actions = ['ode', 'nf']

        filename = os.path.join(self.dirname, 'task.bngl')
        write_task(task, filename)

        with open(filename, 'r') as file:
            lines = file.readlines()

        self.assertEqual(lines, [
            'begin model\n',
            'begin parameters\n',
            '    k_1 0.0\n',
            '    r_2 0.0\n',
            'end parameters\n',
            'begin molecule types\n',
            '    A()\n',
            '    B()\n',
            '    C()\n',
            'end molecule types\n',
            'end model\n',
            'ode\n',
            'nf\n',
        ])

        task2 = read_task(filename)
        self.assertTrue(task2.is_equal(task))

    def test_read_task(self):
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('ignored before content\n')
            file.write('\n')
            file.write('begin model\n')
            file.write('begin  parameters\n')
            file.write('    k_1  0.0\n')
            file.write('    # k_2 0.0\n')
            file.write('end  parameters\n')
            file.write('end model\n')
            file.write('\n')
            file.write('ode\n')

        with pytest.warns(IgnoredBnglFileContentWarning, match='outside content blocks were ignored'):
            task = read_task(filename)
        self.assertTrue(task.model.is_equal(Model({
            'parameters': ModelBlock(['k_1 0.0'])
        })))
        task.actions = ['ode']

        read_task(os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl'))
        read_task(os.path.join(os.path.dirname(__file__), 'fixtures', 'dolan.bngl'))

    def test_read_task_error_handling(self):
        # no `begin model`
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('\n')

        with self.assertRaisesRegex(ValueError, 'does not contain a model'):
            read_task(filename)

        # no `end model`
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin model\n')

        with self.assertRaisesRegex(ValueError, 'has no termination'):
            read_task(filename)

        # no `begin model`
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin parameters\n')

        with self.assertRaisesRegex(ValueError, 'has no termination'):
            read_task(filename)

        # two parameters blocks
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin model\n')
            file.write('begin parameters\n')
            file.write('    k_1 0.0\n')
            file.write('end parameters\n')
            file.write('begin parameters\n')
            file.write('    k_2 0.0\n')
            file.write('end parameters\n')
            file.write('end model\n')

        with self.assertRaisesRegex(ValueError, 'has a second'):
            read_task(filename)

        # no triple nesting of block
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin model\n')
            file.write('begin parameters\n')
            file.write('    begin parameters\n')
            file.write('    end parameters\n')
            file.write('end parameters\n')
            file.write('end model\n')

        with self.assertRaisesRegex(ValueError, 'is inappropriately nested'):
            read_task(filename)

        # mismatched ending
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin model\n')
            file.write('begin parameters\n')
            file.write('end reactions\n')
            file.write('end model\n')

        with self.assertRaisesRegex(ValueError, 'incorrectly ends'):
            read_task(filename)

        # inappropriately nested content
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin model\n')
            file.write('    k_1 0.0\n')
            file.write('end model\n')

        with pytest.warns(IgnoredBnglFileContentWarning, match='outside content blocks were ignored'):
            read_task(filename)

        # inappropriately nested content
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin parameters\n')
            file.write('begin parameters\n')
            file.write('    k_1 0.0\n')
            file.write('end parameters\n')
            file.write('end parameters\n')

        with self.assertRaisesRegex(ValueError, 'inappropriately nested'):
            read_task(filename)

        # no second model
        filename = os.path.join(self.dirname, 'model.bngl')
        with open(filename, 'w') as file:
            file.write('begin model\n')
            file.write('    k_1 0.0\n')
            file.write('end model\n')
            file.write('begin model\n')
            file.write('    k_1 0.0\n')
            file.write('end model\n')

        with self.assertRaisesRegex(ValueError, 'contains a second model'):
            read_task(filename)

    def test_read_simulation_results(self):
        bionetgen_path = Config().bionetgen_path
        model_filename = os.path.join(os.path.dirname(__file__), 'fixtures', 'test.bngl')
        subprocess.check_call([bionetgen_path, model_filename, '--outdir', self.dirname])

        results = read_simulation_results(os.path.join(self.dirname, 'test.gdat'))
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
