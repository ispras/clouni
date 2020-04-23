import unittest
from toscatranslator import shell


class TestShellCommand(unittest.TestCase):

    def test_validation(self):
        shell.main(['--template-file', 'examples/tosca-server-example.yaml', '--validate-only'])
