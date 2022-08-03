import re
import unittest

from testing.base import TestAnsibleProvider
from shell_clouni import shell
import copy, os, yaml

from toscatranslator.common.tosca_reserved_keys import TOPOLOGY_TEMPLATE, NODE_TEMPLATES, PROPERTIES

INSTANCE_MODULE_NAME = 'ec2_instance'
SEC_GROUP_MODULE_NAME = 'ec2_group'
SUBNET_MODULE_NAME = 'ec2_vpc_subnet'
NETWORK_MODULE_NAME = 'ec2_vpc_net'
PORT_MODULE_NAME = 'ec2_eni'
PUBLIC_ADDRESS = 'public_address'


class TestAnsibleAmazonOutput (unittest.TestCase, TestAnsibleProvider):
    PROVIDER = 'amazon'

    def test_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path, '--debug'])
        file_diff_path = os.path.join('examples', 'tosca-server-example-ansible-amazon.yaml')
        self.diff_files(file_output_path, file_diff_path)

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
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--validate-only', '--debug'])

    def test_translating_to_ansible(self):
        shell.main(['--template-file', 'examples/tosca-server-example-amazon.yaml', '--cluster-name',
                    'test', '--provider', self.PROVIDER, '--debug'])

    def test_full_translating_network(self):
        file_path = os.path.join('examples', 'tosca-network-and-port-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-network-and-port-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path, '--debug'])

        file_diff_path = os.path.join('examples', 'tosca-network-and-port-example-ansible-amazon.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_server_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        playbook = self.get_ansible_create_output(template)
        self.assertEqual(len(playbook), 2)
        for play in playbook:
            self.assertIsInstance(play, dict)
            self.assertIsNotNone(play['tasks'])
        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        self.assertEqual(len(tasks), 15)
        self.assertIsNotNone(tasks[6][INSTANCE_MODULE_NAME])
        server = tasks[6][INSTANCE_MODULE_NAME]
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
        instance_name = None
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('vpc_subnet_id'))
                instance_name = task[INSTANCE_MODULE_NAME]['name']
                instance_subnet = task[INSTANCE_MODULE_NAME]['vpc_subnet_id']
        self.assertIsNotNone(instance_name)
        self.assertIsNotNone(instance_subnet)

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

    def test_network_name(self):
        super(TestAnsibleAmazonOutput, self).test_network_name()

    def test_host_capabilities(self):
        super(TestAnsibleAmazonOutput, self).test_host_capabilities()

    def test_get_property(self):
        super(TestAnsibleAmazonOutput, self).test_get_property()

    def check_get_property(self, tasks, testing_value=None):
        checked = True
        for task in tasks:
            ec2_instance_task = task.get('ec2_instance', None)
            if ec2_instance_task != None and ec2_instance_task.get('tags', {}).get('metadata', None) != testing_value:
                checked = False
        self.assertTrue(checked)

    def test_host_of_software_component(self):
        super(TestAnsibleAmazonOutput, self).test_host_of_software_component()

    def check_host_of_software_component(self, playbook):
        self.assertEqual(len(playbook), 3)
        for play in playbook:
            self.assertIsNotNone(play.get('tasks'))

        self.assertEqual(playbook[2].get('hosts'), self.NODE_NAME + '_instance_public_address')
        tasks2 = playbook[2]['tasks']
        tasks1 = playbook[0]['tasks'] + playbook[1]['tasks']
        tasks = tasks1

        checked = False
        for i in range(len(tasks)):
            if tasks[i].get('ec2_instance', None) != None:
                pip_var = tasks[i]['register']

                self.assertIsNotNone(tasks[i + 1].get('set_fact', {}).get('ansible_user'))
                self.assertIsNotNone(tasks[i + 2].get('set_fact', None))
                self.assertEqual(tasks[i + 2]['set_fact'].get('host_ip', None),
                                 '{{ host_ip | default([]) + [[ "tosca_server_example_public_address_" + item, ' +
                                 pip_var + '.results[item | int - 1].instances[0].public_ip_address ]] }}')

                self.assertEqual(tasks[i + 3].get('set_fact', {}).get('group'), self.NODE_NAME + '_instance_public_address')
                self.assertIsNotNone(tasks[i + 4].get('include', None))
                self.assertEqual(tasks[i + 4]['include'], '/tmp/clouni/test/artifacts/add_host.yaml')
                checked = True
        self.assertTrue(checked)

        tasks = tasks2
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].get('set_fact', {}).get('version', None), 0.1)
        self.assertEqual(tasks[1].get('include', None), "/tmp/clouni/test/artifacts/examples/ansible-server-example.yaml")

    def test_nodes_interfaces_operations(self):
        super(TestAnsibleAmazonOutput, self).test_nodes_interfaces_operations()

    def check_nodes_interfaces_operations(self, plays, testing_value):
        self.assertEqual(len(plays), 5)

        for play in plays:
            self.assertIsNotNone(play.get('tasks'))
            self.assertEqual(play.get('hosts'), 'localhost')

        self.assertTrue('create' in plays[1].get('name'))
        self.assertTrue('configure' in plays[2].get('name'))
        self.assertTrue('start' in plays[3].get('name'))
        self.assertTrue('stop' in plays[4].get('name'))

        checked = False
        for task in plays[1]['tasks']:
            if task.get('ec2_instance'):
                checked = True
        self.assertTrue(checked)

        for i in range(2, 5):
            self.assertEqual(plays[i]['tasks'][0].get('set_fact', {}).get(testing_value), testing_value)
            self.assertEqual(plays[i]['tasks'][1].get('include'), '/tmp/clouni/test/artifacts/examples/ansible-operation-example.yaml')

    def test_scalable_capabilities(self):
        super(TestAnsibleAmazonOutput, self).test_scalable_capabilities()

    def check_scalable_capabilities(self, tasks, testing_value=None):
        server_name = None
        default_instances = 2
        if testing_value:
            default_instances = testing_value.get('default_instances', default_instances)
        for task in tasks:
            if task.get(INSTANCE_MODULE_NAME):
                self.assertIsNotNone(task.get('with_sequence'))
                self.assertIsNotNone(task[INSTANCE_MODULE_NAME].get('name'))
                self.assertTrue(task['with_sequence'], 'start=1 end=' + str(default_instances) + ' format=')
                server_name = task[INSTANCE_MODULE_NAME]['name']
        self.assertIsNotNone(server_name)

    def test_relationships_interfaces_operations(self):
        super(TestAnsibleAmazonOutput, self).test_relationships_interfaces_operations()

    def check_relationships_interfaces_operations(self, plays, rel_name, soft_name, testing_value):
        self.assertEqual(len(plays), 10)
        for play in plays:
            self.assertIsNotNone(play.get('tasks'))

        self.assertTrue('create' in plays[0].get('name'))
        self.assertTrue('create' in plays[1].get('name'))

        checked = False
        for task in plays[1]['tasks']:
            if task.get('ec2_instance'):
                checked = True
        self.assertTrue(checked)

        self.assertTrue('pre_configure_target' in plays[2].get('name'))
        self.assertTrue(rel_name + '_hosted_on' in plays[2].get('name'))
        self.assertEqual(plays[2].get('hosts'), 'localhost')

        self.assertTrue('configure' in plays[3].get('name'))

        self.assertTrue('post_configure_target' in plays[4].get('name'))
        self.assertTrue(rel_name + '_hosted_on' in plays[4].get('name'))
        self.assertEqual(plays[4].get('hosts'), 'localhost')


        self.assertTrue('create' in plays[5].get('name'))
        self.assertTrue(soft_name + '_server_example' in plays[5].get('name'))

        if 'pre_configure_source' in plays[6].get('name'):
            self.assertTrue(rel_name+ '_hosted_on' in plays[6].get('name'))
            self.assertEqual(plays[6].get('hosts'), 'tosca_server_example_instance_public_address')

            self.assertTrue('add_source' in plays[7].get('name'))
            self.assertTrue(rel_name + '_hosted_on' in plays[7].get('name'))
            self.assertEqual(plays[7].get('hosts'), 'localhost')
        elif 'add_source' in plays[6].get('name'):
            self.assertTrue(rel_name + '_hosted_on' in plays[6].get('name'))
            self.assertEqual(plays[6].get('hosts'), 'localhost')

            self.assertTrue('pre_configure_source' in plays[7].get('name'))
            self.assertTrue(rel_name + '_hosted_on' in plays[7].get('name'))
            self.assertEqual(plays[7].get('hosts'), 'tosca_server_example_instance_public_address')
        else:
            self.assertTrue(False)

        self.assertTrue('configure' in plays[8].get('name'))
        self.assertTrue(soft_name+ '_server_example' in plays[8].get('name'))

        self.assertTrue('post_configure_source' in plays[9].get('name'))
        self.assertTrue(rel_name + '_hosted_on' in plays[9].get('name'))
        self.assertEqual(plays[9].get('hosts'), 'tosca_server_example_instance_public_address')

        for i in range(2, 10):
            self.assertEqual(plays[i]['tasks'][0].get('set_fact', {}).get(testing_value), testing_value)
            self.assertEqual(plays[i]['tasks'][1].get('include'), '/tmp/clouni/test/artifacts/examples/ansible-operation-example.yaml')
