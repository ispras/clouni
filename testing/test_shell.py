import unittest
from toscatranslator import shell

import os


class TestShellCommand(unittest.TestCase):

    def test_validation(self):
        shell.main(['--template-file', 'examples/tosca-server-example.yaml', '--validate-only', '--cluster-name', 'test'])

    def test_validate_change_wd(self):
        working_directory = os.getcwd()
        os.chdir('examples')
        try:
            shell.main(['--template-file', 'tosca-server-example.yaml', '--validate-only', '--cluster-name', '--test'])
        finally:
            os.chdir(working_directory)
