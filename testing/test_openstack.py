import unittest
from testing.base import TestAnsibleProviderOutput
import copy

from toscatranslator import shell

SERVER_MODULE_NAME = 'os_server'
PORT_MODULE_NAME = 'os_port'
FIP_MODULE_NAME = 'os_floating_ip'
SEC_GROUP_MODULE_NAME = 'os_security_group'
SEC_RULE_MODULE_NAME = 'os_security_group_rule'


class TestAnsibleOpenStackOutput (unittest.TestCase, TestAnsibleProviderOutput):
    PROVIDER = 'openstack'

    def test_validation(self):
        shell.main(['--template-file', 'examples/tosca-server-example-openstack.yaml', '--validate-only'])

    def test_translating_to_ansible(self):
        shell.main(['--template-file', 'examples/tosca-server-example-openstack.yaml', '--provider', self.PROVIDER])

    def test_full_translating(self):
        shell.main(['--template-file', 'examples/tosca-server-example.yaml', '--provider', self.PROVIDER])

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
        testing_value = ["master=true"]
        testing_parameter = {
            "meta": testing_value
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))
        tasks = playbook[0]['tasks']

        self.check_meta(tasks, testing_value)

    def check_meta (self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('meta'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_meta = task[SERVER_MODULE_NAME]['meta']
                if testing_value:
                    self.assertEqual(server_meta, testing_value)
        self.assertIsNotNone(server_name)

    def test_private_address(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_value = "192.168.12.25"
        testing_parameter = {
            "private_address": testing_value
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))
        tasks = playbook[0]['tasks']

        self.check_private_address(tasks, testing_value)

    def check_private_address(self, tasks, testing_value=None):
        port_name = None
        server_nics = None
        for task in tasks:
            if task.get(PORT_MODULE_NAME):
                self.assertIsNotNone(task[PORT_MODULE_NAME].get("name"))
                self.assertIsNotNone(task[PORT_MODULE_NAME].get("fixed_ips"))
                port_name = task[PORT_MODULE_NAME]['name']
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('nics'))
                server_nics = task[SERVER_MODULE_NAME]['nics']
                self.assertIsNotNone(port_name)
                self.assertIn(port_name, server_nics)
        self.assertIsNotNone(server_nics)

    def test_public_address(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_value = "10.100.115.15"
        testing_parameter = {
            "public_address": testing_value
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = playbook[0]['tasks']
        self.check_public_address(tasks, testing_value)

    def check_public_address(self, tasks, testing_value=None):
        fip_server = None
        server_name = None
        for task in tasks:
            if task.get(FIP_MODULE_NAME):
                self.assertIsNotNone(task[FIP_MODULE_NAME].get("network"))
                self.assertIsNotNone(task[FIP_MODULE_NAME].get("floating_ip_address"))
                self.assertIsNotNone(task[FIP_MODULE_NAME].get("server"))
                fip_server = task[FIP_MODULE_NAME]['server']
                self.assertIsNotNone(server_name)
                self.assertEqual(fip_server, server_name)
                floating_ip = task[FIP_MODULE_NAME]['floating_ip_address']
                self.assertEqual(floating_ip, testing_value)
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                server_name = task[SERVER_MODULE_NAME]['name']
        self.assertIsNotNone(fip_server)

    def test_network_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_value = "test-two-routers"
        testing_parameter = {
            "networks": {
                "default": {
                    "name": testing_value
                }
            }
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = playbook[0]['tasks']
        self.check_network_name(tasks, testing_value)

    def check_network_name(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('nics'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_nics = task[SERVER_MODULE_NAME]['nics']
                if testing_value:
                    self.assertIn(testing_value, server_nics)
        self.assertIsNotNone(server_name)

    def test_host_capabilities(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "num_cpus": 1,
            "disk_size": "160 GiB",
            "mem_size": "1024 MiB"
        }
        template = self.update_template_capability_properties(template, self.NODE_NAME, "host", testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = playbook[0]['tasks']
        self.check_host_capabilities(tasks)

    def check_host_capabilities(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('flavor'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_flavor = task[SERVER_MODULE_NAME]['flavor']
                if testing_value:
                    self.assertEqual(server_flavor, testing_value)
        self.assertIsNotNone(server_name)

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
        playbook = self.get_ansible_output(template)
        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = playbook[0]['tasks']
        self.check_endpoint_capabilities(tasks)

    def check_endpoint_capabilities(self, tasks, testing_value=None):
        sec_group_name = None
        if_sec_rule = False
        server_name = None
        for task in tasks:
            if task.get(SEC_GROUP_MODULE_NAME):
                self.assertIsNotNone(task[SEC_GROUP_MODULE_NAME].get('name'))
                sec_group_name = task[SEC_GROUP_MODULE_NAME]['name']
                self.assertFalse(if_sec_rule)
                self.assertIsNone(server_name)
            if task.get(SEC_RULE_MODULE_NAME):
                self.assertIsNotNone(task[SEC_RULE_MODULE_NAME].get('direction'))
                self.assertIsNotNone(task[SEC_RULE_MODULE_NAME].get('port_range_min'))
                self.assertIsNotNone(task[SEC_RULE_MODULE_NAME].get('port_range_max'))
                self.assertIsNotNone(task[SEC_RULE_MODULE_NAME].get('protocol'))
                self.assertIsNotNone(task[SEC_RULE_MODULE_NAME].get('remote_ip_prefix'))
                self.assertIsNotNone(task[SEC_RULE_MODULE_NAME].get('security_group'))
                if_sec_rule = True
                self.assertIsNotNone(sec_group_name)
                rule_group_name = task[SEC_RULE_MODULE_NAME]['security_group']
                self.assertEqual(rule_group_name, sec_group_name)
                self.assertIsNone(server_name)
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('security_groups'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_groups = task[SERVER_MODULE_NAME]['security_groups']
                self.assertIsNotNone(sec_group_name)
                self.assertIn(sec_group_name, server_groups)
        self.assertIsNotNone(server_name)

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
        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = playbook[0]['tasks']
        self.check_os_capabilities(tasks)

    def check_os_capabilities(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('image'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_image = task[SERVER_MODULE_NAME]['image']
                if testing_value:
                    self.assertEqual(testing_value, server_image)
        self.assertIsNotNone(server_name)

    def test_multiple_relationships(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        testing_parameter = {
            "public_address": "10.100.115.15",
            "private_address": "192.168.12.25"
        }
        template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = playbook[0]['tasks']
        self.check_public_address(tasks, "10.100.115.15")
        self.check_private_address(tasks, "192.168.12.25")
