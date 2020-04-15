""" Tests of the BioNetGen command-line interface and Docker image

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-04-07
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""


from Biosimulations_bionetgen import __main__
try:
    from Biosimulations_utils.simulator.testing import SimulatorValidator
except ModuleNotFoundError:
    pass
import Biosimulations_bionetgen
import capturer
try:
    import docker
except ModuleNotFoundError:
    pass
import numpy
import os
import pandas
import shutil
import tempfile
import unittest


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def test_help(self):
        with self.assertRaises(SystemExit):
            with __main__.App(argv=['--help']) as app:
                app.run()

    def test_version(self):
        with __main__.App(argv=['-v']) as app:
            with capturer.CaptureOutput(merged=False, relay=False) as captured:
                with self.assertRaises(SystemExit):
                    app.run()
                self.assertIn(Biosimulations_bionetgen.__version__, captured.stdout.get_text())
                self.assertEqual(captured.stderr.get_text(), '')

        with __main__.App(argv=['--version']) as app:
            with capturer.CaptureOutput(merged=False, relay=False) as captured:
                with self.assertRaises(SystemExit):
                    app.run()
                self.assertIn(Biosimulations_bionetgen.__version__, captured.stdout.get_text())
                self.assertEqual(captured.stderr.get_text(), '')

    def test_sim_short_arg_names(self):
        archive_filename = 'tests/fixtures/test.omex'
        with __main__.App(argv=['-i', archive_filename, '-o', self.dirname]) as app:
            app.run()
        self.assert_outputs_created(self.dirname)

    def test_sim_long_arg_names(self):
        archive_filename = 'tests/fixtures/test.omex'
        with __main__.App(argv=['--archive', archive_filename, '--out-dir', self.dirname]) as app:
            app.run()
        self.assert_outputs_created(self.dirname)

    @unittest.skipIf(os.getenv('CI', '0') in ['1', 'true'], 'Docker not setup in CI')
    def test_build_docker_image(self):
        docker_client = docker.from_env()

        # build image
        image_repo = 'crbm/biosimulations_bionetgen'
        image_tag = Biosimulations_bionetgen.__version__
        image, _ = docker_client.images.build(
            path='.',
            dockerfile='Dockerfile',
            pull=True,
            rm=True,
        )
        image.tag(image_repo, tag='latest')
        image.tag(image_repo, tag=image_tag)

    @unittest.skipIf(os.getenv('CI', '0') in ['1', 'true'], 'Docker not setup in CI')
    def test_sim_with_docker_image(self):
        docker_client = docker.from_env()

        # image config
        image_repo = 'crbm/biosimulations_bionetgen'
        image_tag = Biosimulations_bionetgen.__version__

        # setup input and output directories
        in_dir = os.path.join(self.dirname, 'in')
        out_dir = os.path.join(self.dirname, 'out')
        os.makedirs(in_dir)
        os.makedirs(out_dir)

        # create intermediate directories so that the test runner will have permissions to cleanup the results generated by
        # the docker image (running as root)
        os.makedirs(os.path.join(out_dir, 'test'))

        # copy model and simulation to temporary directory which will be mounted into container
        shutil.copyfile('tests/fixtures/test.omex', os.path.join(in_dir, 'test.omex'))

        # run image
        container = docker_client.containers.run(
            image_repo + ':' + image_tag,
            volumes={
                in_dir: {
                    'bind': '/root/in',
                    'mode': 'ro',
                },
                out_dir: {
                    'bind': '/root/out',
                    'mode': 'rw',
                }
            },
            command=['-i', '/root/in/test.omex', '-o', '/root/out'],
            tty=True,
            detach=True)
        status = container.wait()
        if status['StatusCode'] != 0:
            raise RuntimeError(container.logs().decode().replace('\\r\\n', '\n').strip())
        container.stop()
        container.remove()

        self.assert_outputs_created(out_dir)

    def assert_outputs_created(self, dirname):
        self.assertEqual(set(os.listdir(dirname)), set(['test']))
        self.assertEqual(set(os.listdir(os.path.join(dirname, 'test'))), set(['simulation_1.csv']))

        results = pandas.read_csv(os.path.join(dirname, 'test', 'simulation_1.csv'))

        # test that the results have the correct time points
        numpy.testing.assert_array_almost_equal(results['time'], numpy.linspace(0., 10., 101))

        # test that the results have the correct row labels (observable ids)
        var_ids = set([
            'Atot',
            'Btot',
            'GA00tot',
            'GA01tot',
            'GA10tot',
            'GB00tot',
            'GB01tot',
            'GB10tot',
        ])
        self.assertEqual(set(results.columns.to_list()), var_ids | set(['time']))

    @unittest.skipIf(os.getenv('CI', '0') in ['1', 'true'], 'Docker not setup in CI')
    def test_validator(self):
        validator = SimulatorValidator()
        valid_cases, case_exceptions = validator.run('crbm/biosimulations_bionetgen', 'properties.json')
        self.assertGreater(len(valid_cases), 0)
        self.assertEqual(case_exceptions, [])
