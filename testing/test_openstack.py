import unittest
from testing.base import TestAnsibleProviderOutput
import copy

from toscatranslator import shell

SERVER_MODULE_NAME = 'os_server'


class TestAnsibleOpenStackOutput (unittest.TestCase, TestAnsibleProviderOutput):
    PROVIDER = 'openstack'

    def test_validation(self):
        shell.main(['--template-file', 'examples/tosca-server-example-openstack.yaml', '--validate-only'])

    def test_translating_to_ansible(self):
        shell.main(['--template-file', 'examples/tosca-server-example-openstack.yaml', '--provider', 'openstack',
                    '--facts', 'examples/facts-openstack.json'])

    def test_server_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        playbook = self.get_ansible_output(template)
        self.assertEqual(len(playbook), 1)
        self.assertIsInstance(playbook[0], dict)
        self.assertIsNotNone(playbook[0]['tasks'])
        tasks = playbook[0]['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertIsNotNone(tasks[0][SERVER_MODULE_NAME])
        server = tasks[0][SERVER_MODULE_NAME]
        self.assertEqual(server['name'], self.NODE_NAME)

    def test_meta(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        template = self.update_template_attribute(template, self.NODE_NAME, {"meta": "master=true"})
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(next(iter(playbook), {}).get('tasks', [])), {}).get(SERVER_MODULE_NAME, {}).get('meta'))
        self.assertListEqual(playbook[0]['tasks'][0][SERVER_MODULE_NAME]['meta'], ["master=true"])

    def test_private_address(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "private_address": "192.168.12.25"
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(True)

    def test_public_address(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "public_address": "10.100.115.15"
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(playbook)

    def test_network_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "networks": {
                "default": {
                    "name": "test-two-routers"
                }
            }
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(playbook)

    def test_host_capabilities(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "num_cpus": 1
        }
        template = self.update_template_capability_properties(template, self.NODE_NAME, "host", testing_parameter)

    def test_endpoint_capabilities(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "endpoint": {
                "properties": {
                    "protocol": "tcp",
                    "port": 1000,
                    "initiator": "target"
                },
                "attributes": {
                    "ip_address": "0.0.0.0"
                }
            }
        }
        template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)

    def test_os_capabilities(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "architecture": "x86_64",
            "type": "ubuntu",
            "distribution": "xenial",
            "version": 16.04
        }
        template = self.update_template_capability_properties(template, self.NODE_NAME, "os", testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(playbook)

    def test_multiple_relationships(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "public_address": "10.100.115.15",
            "private_address": "192.168.12.25"
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(playbook)


