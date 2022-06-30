import unittest

from testing.base import TestAnsibleProvider
from shell_clouni import shell
import copy, os, yaml

from toscatranslator.common.tosca_reserved_keys import TOPOLOGY_TEMPLATE, NODE_TEMPLATES, PROPERTIES

INSTANCE_MODULE_NAME = 'ec2_instance'
SEC_GROUP_MODULE_NAME = 'ec2_group'
PUBLIC_ADDRESS = 'public_address'


class TestAnsibleAmazonOutput (unittest.TestCase, TestAnsibleProvider):
    PROVIDER = 'amazon'

    @unittest.expectedFailure
    def test_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path])

    def test_full_translating_no_public(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        template_raw = self.read_template(file_path)
        template = yaml.load(template_raw, Loader=yaml.Loader)
        template[TOPOLOGY_TEMPLATE][NODE_TEMPLATES][self.NODE_NAME][PROPERTIES].pop(PUBLIC_ADDRESS)
        template[TOPOLOGY_TEMPLATE][NODE_TEMPLATES][self.NODE_NAME][PROPERTIES].pop('networks')
        playbook = self.get_ansible_create_output(template)
        self.assertIsNotNone(playbook)

    def test_validation(self):
        # Public address is not supported in AWS
        file_path = os.path.join('examples', 'tosca-server-example-amazon.yaml')
        shell.main(['--template-file', file_path, '--validate-only', '--cluster-name', 'test'])

    def test_translating_to_ansible(self):
        shell.main(['--template-file', 'examples/tosca-server-example-amazon.yaml', '--provider', self.PROVIDER,
                    '--cluster-name', 'test'])

    def test_server_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        playbook = self.get_ansible_create_output(template)
        self.assertEqual(len(playbook), 1)
        for play in playbook:
            self.assertIsInstance(play, dict)
            self.assertIsNotNone(play['tasks'])
        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        self.assertEqual(len(tasks), 10)
        self.assertIsNotNone(tasks[2][INSTANCE_MODULE_NAME])
        server = tasks[2][INSTANCE_MODULE_NAME]
        self.assertEqual(server['name'], self.NODE_NAME)

    def test_meta(self, extra=None):
        super(TestAnsibleAmazonOutput, self).test_meta(extra=extra)

    def check_meta (self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('tags', {}).get('metadata'))
                server_name = task[INSTANCE_MODULE_NAME]['name']
                server_meta = task[INSTANCE_MODULE_NAME]['tags']['metadata']
                if testing_value:
                    self.assertEqual(server_meta, testing_value)
        self.assertIsNotNone(server_name)

    def test_private_address(self):
        super(TestAnsibleAmazonOutput, self).test_private_address()

    def check_private_address(self, tasks, testing_value=None):
        server_private_ip = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get("network", {}).get('private_ip_address'))
                server_private_ip = task[INSTANCE_MODULE_NAME]['network']['private_ip_address']
                if testing_value:
                    self.assertEqual(server_private_ip, testing_value)
        self.assertIsNotNone(server_private_ip)

    def check_network_name(self, tasks, testing_value=None):
        # NOTE must be an error, but nothing happens
        pass

    def test_host_capabilities(self):
        super(TestAnsibleAmazonOutput, self).test_host_capabilities()

    def check_host_capabilities(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('instance_type'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                server_name = task[INSTANCE_MODULE_NAME]['instance_type']
                server_flavor = task[INSTANCE_MODULE_NAME]['instance_type']
                if testing_value:
                    self.assertEqual(server_flavor, testing_value)
        self.assertIsNotNone(server_name)

    def test_endpoint_capabilities(self):
        super(TestAnsibleAmazonOutput, self).test_endpoint_capabilities()

    def check_endpoint_capabilities(self, tasks, testing_value=None):
        sec_group_name = None
        server_name = None
        for task in tasks:
            if task.get(SEC_GROUP_MODULE_NAME):
                self.assertIsNotNone(task[SEC_GROUP_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[SEC_GROUP_MODULE_NAME].get('rules'))
                sec_group_name = task[SEC_GROUP_MODULE_NAME]['name']
                self.assertIsNone(server_name)
                sec_rules = task[SEC_GROUP_MODULE_NAME]['rules']
                if_rule = False
                for rule in sec_rules:
                    if rule.get('cidr_ip') and rule.get('proto') and rule.get('ports'):
                        if_rule = True
                        break
                self.assertTrue(if_rule)

            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('security_groups'))
                server_name = task[INSTANCE_MODULE_NAME]['name']
                server_groups = task[INSTANCE_MODULE_NAME]['security_groups']
                self.assertIsNotNone(sec_group_name)
                self.assertIn(sec_group_name, server_groups)
        self.assertIsNotNone(server_name)

    def test_os_capabilities(self):
        super(TestAnsibleAmazonOutput, self).test_os_capabilities()

    def check_os_capabilities(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('image_id'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                server_name = task[INSTANCE_MODULE_NAME]['name']
        self.assertIsNotNone(server_name)

    @unittest.expectedFailure
    def test_network_name(self):
        super(TestAnsibleAmazonOutput, self).test_network_name()

    def test_host_capabilities(self):
        super(TestAnsibleAmazonOutput, self).test_host_capabilities()