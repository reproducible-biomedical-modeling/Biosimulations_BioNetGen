from biosimulators_bionetgen.config import Config
from unittest import mock
import os
import unittest


class ConfigTestCase(unittest.TestCase):
    def test_Config(self):
        with mock.patch.dict(os.environ, {'BIONETGEN_PATH': 'BNG2.pl'}):
            self.assertEqual(Config().bionetgen_path, 'BNG2.pl')

        with mock.patch.dict(os.environ, {'BIONETGEN_PATH': '/path/to/BNG2.pl'}):
            self.assertEqual(Config().bionetgen_path, '/path/to/BNG2.pl')
