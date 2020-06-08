from testing.base import TestAnsibleProvider, shell
import copy
import unittest


INSTANCE_MODULE_NAME = 'ec2_instance'
SEC_GROUP_MODULE_NAME = 'ec2_group'


class TestAnsibleAmazonOutput (unittest.TestCase, TestAnsibleProvider):
    PROVIDER = 'amazon'

    def test_validation(self):
        # Public address is not supported in AWS
        shell.main(['--template-file', 'examples/tosca-server-example-amazon.yaml', '--validate-only'])

    def test_translating_to_ansible(self):
        shell.main(['--template-file', 'examples/tosca-server-example-amazon.yaml', '--provider', self.PROVIDER])

    def test_server_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        playbook = self.get_ansible_output(template)
        self.assertEqual(len(playbook), 1)
        self.assertIsInstance(playbook[0], dict)
        self.assertIsNotNone(playbook[0]['tasks'])
        tasks = playbook[0]['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertIsNotNone(tasks[0][INSTANCE_MODULE_NAME])
        server = tasks[0][INSTANCE_MODULE_NAME]
        self.assertEqual(server['name'], self.NODE_NAME)

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

    def check_private_address(self, tasks, testing_value=None):
        server_private_ip = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get("network", {}).get('interface', {})
                                     .get('properties', {}).get('private_ip_address'))
                server_private_ip = task[INSTANCE_MODULE_NAME]['network']['interface']['properties']['private_ip_address']
                if testing_value:
                    self.assertEqual(server_private_ip, testing_value)
        self.assertIsNotNone(server_private_ip)

    def check_network_name(self, tasks, testing_value=None):
        # NOTE must be an error, but nothing happens
        pass

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

    def check_os_capabilities(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('image_id'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                server_name = task[INSTANCE_MODULE_NAME]['name']
        self.assertIsNotNone(server_name)
