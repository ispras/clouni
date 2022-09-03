import sys
import unittest
from shutil import copyfile

import six
from yaml import Loader

from testing.base import TestAnsibleProvider

import copy, os, re, yaml
from shell_clouni import shell
from toscatranslator.common import utils

SERVER_MODULE_NAME = 'os_server'
PORT_MODULE_NAME = 'os_port'
FIP_MODULE_NAME = 'os_floating_ip'
SEC_GROUP_MODULE_NAME = 'os_security_group'
SEC_RULE_MODULE_NAME = 'os_security_group_rule'
NETWORK_MODULE_NAME = 'os_network'
SUBNET_MODULE_NAME = 'os_subnet'

SUCCESS_CHECK_FILE = 'successful_tasks.yaml'

class TestAnsibleOpenStackOutput (unittest.TestCase, TestAnsibleProvider):
    PROVIDER = 'openstack'

    def test_validation(self):
        file_path = os.path.join('examples', 'tosca-server-example-openstack.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--validate-only', '--debug'])

    def test_translating_to_ansible(self):
        file_path = os.path.join('examples', 'tosca-server-example-openstack.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--debug'])

    def test_translating_to_ansible_delete(self):
        file_path = os.path.join('examples', 'tosca-server-example-openstack.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--delete','false','--provider', self.PROVIDER, '--debug'])

    def test_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path, '--debug'])

        file_diff_path = os.path.join('examples', 'tosca-server-example-ansible-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_delete_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output-delete.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--delete',
                    '--output-file', file_output_path, '--debug'])

        file_diff_path = os.path.join('examples', 'tosca-server-example-ansible-delete-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_full_translating_network(self):
        file_path = os.path.join('examples', 'tosca-network-and-port-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-network-and-port-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path, '--debug'])

        file_diff_path = os.path.join('examples', 'tosca-network-and-port-example-ansible-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_delete_full_translating_network(self):
        file_path = os.path.join('examples', 'tosca-network-and-port-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-network-and-port-example-output-delete.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--delete',
                    '--output-file', file_output_path, '--debug'])

        file_diff_path = os.path.join('examples', 'tosca-network-and-port-example-ansible-delete-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_volume_validation(self):
        file_path = os.path.join('examples', 'tosca-volume-example.yaml')
        file_output = os.path.join('examples', 'tosca-volume-output.yaml')
        shell.main(
            ['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--output-file',
             file_output, '--delete', '--debug'])
        file_diff_path = os.path.join('examples', 'tosca-volume-correct.yaml')
        self.diff_files(file_output, file_diff_path)

    def test_network_with_compute(self):
        file_path = os.path.join('examples', 'tosca-network-and-server-example.yaml')
        template = self.read_template(file_path)
        playbook = self.get_ansible_create_output(template, file_path, delete_template=False)
        self.assertEqual(len(playbook), 5)
        for elem in playbook:
            self.assertIsInstance(elem, dict)
            self.assertIsNotNone(elem['tasks'])
        has_network = False
        has_subnet = False
        has_port = False
        has_compute = False
        for elem in playbook:
            tasks = elem['tasks']
            for task in tasks:
                if not has_network:
                    if task.get(SUBNET_MODULE_NAME) or task.get(PORT_MODULE_NAME) or task.get(SERVER_MODULE_NAME):
                        self.assertTrue(False, msg='os_network should be first!')
                    if task.get(NETWORK_MODULE_NAME):
                        self.check_network_module(task)
                        network_name = task[NETWORK_MODULE_NAME]['name']
                        has_network = True
                elif has_network:
                    if not has_subnet:
                        if task.get(PORT_MODULE_NAME) or task.get(SERVER_MODULE_NAME):
                            self.assertTrue(False, msg='os_subnet should be first!')
                        if task.get(SUBNET_MODULE_NAME):
                            self.check_subnet_module(task, network_name)
                            subnet_name = task[SUBNET_MODULE_NAME]['name']
                            has_subnet = True
                    elif has_subnet:
                        if not has_port:
                            if task.get(SERVER_MODULE_NAME):
                                self.assertTrue(False, msg='os_port should be first!')
                            if task.get(PORT_MODULE_NAME):
                                self.check_port_module(task, subnet_name)
                                port_name = task[PORT_MODULE_NAME]['name']
                                has_port = True
                        elif has_port:
                            if task.get(SERVER_MODULE_NAME):
                                self.check_compute_module(task, port_name)
                                has_compute = True
        self.assertTrue(has_network)
        self.assertTrue(has_subnet)
        self.assertTrue(has_port)
        self.assertTrue(has_compute)

    def check_compute_module(self, task, port_name):
        self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
        self.assertIsNotNone(task[SERVER_MODULE_NAME].get('nics'))
        self.assertIsNotNone(task[SERVER_MODULE_NAME].get('image'))
        self.assertIsNotNone(task[SERVER_MODULE_NAME].get('flavor'))
        nics = task[SERVER_MODULE_NAME]['nics']
        self.assertIsNotNone(port_name)
        port_found = False
        for nic in nics:
            if nic.get('port-name', '') == port_name:
                port_found = True
                break
        self.assertTrue(port_found)

    def check_network_module(self, task):
        self.assertIsNotNone(task[NETWORK_MODULE_NAME].get('name'))
        self.assertIsNotNone(task[NETWORK_MODULE_NAME].get('provider_network_type'))

    def check_port_module(self, task, subnet_name):
        self.assertIsNotNone(task[PORT_MODULE_NAME].get('admin_state_up'))
        self.assertIsNotNone(task[PORT_MODULE_NAME].get('name'))
        self.assertIsNotNone(task[PORT_MODULE_NAME].get('port_security_enabled'))
        self.assertIsNotNone(task[PORT_MODULE_NAME].get('network'))
        subnet_network_name = task[PORT_MODULE_NAME]['network']
        self.assertEqual(subnet_network_name, subnet_name)

    def check_subnet_module(self, task, network_name):
        self.assertIsNotNone(task[SUBNET_MODULE_NAME].get('allocation_pool_end'))
        self.assertIsNotNone(task[SUBNET_MODULE_NAME].get('allocation_pool_start'))
        self.assertIsNotNone(task[SUBNET_MODULE_NAME].get('cidr'))
        self.assertIsNotNone(task[SUBNET_MODULE_NAME].get('gateway_ip'))
        self.assertIsNotNone(task[SUBNET_MODULE_NAME].get('name'))
        self.assertIsNotNone(task[SUBNET_MODULE_NAME].get('network_name'))
        subnet_network_name = task[SUBNET_MODULE_NAME]['network_name']
        self.assertEqual(subnet_network_name, network_name)

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
        self.assertEqual(len(tasks), 26)
        self.assertIsNotNone(tasks[13][SERVER_MODULE_NAME])
        server = tasks[13][SERVER_MODULE_NAME]
        self.assertEqual(server['name'], self.NODE_NAME)

    def test_meta(self, extra=None):
        super(TestAnsibleOpenStackOutput, self).test_meta(extra=extra)

    def check_meta (self, tasks, testing_value=None, extra=None):
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
        super(TestAnsibleOpenStackOutput, self).test_private_address()

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
                port_found = False
                for nic_info in server_nics:
                    if nic_info.get('port-name', '') == port_name:
                        port_found = True
                        break
                self.assertTrue(port_found)
        self.assertIsNotNone(server_nics)

    def test_public_address(self):
        super(TestAnsibleOpenStackOutput, self).test_public_address()

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
        super(TestAnsibleOpenStackOutput, self).test_network_name()

    def check_network_name(self, tasks, testing_value=None):
        server_name = None
        for task in tasks:
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('nics'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_nics = task[SERVER_MODULE_NAME]['nics']
                if testing_value:
                    nic_found = False
                    for nic_info in server_nics:
                        if nic_info.get('net-name', '') == testing_value:
                            nic_found = True
                            break
                    self.assertTrue(nic_found)
        self.assertIsNotNone(server_name)

    def test_host_capabilities(self):
        super(TestAnsibleOpenStackOutput, self).test_host_capabilities()

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
        super(TestAnsibleOpenStackOutput, self).test_endpoint_capabilities()

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
                # self.assertIsNone(server_name)
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('security_groups'))
                server_name = task[SERVER_MODULE_NAME]['name']
                server_groups = task[SERVER_MODULE_NAME]['security_groups']
                self.assertIsNotNone(sec_group_name)
                self.assertIn(sec_group_name, server_groups)
        self.assertIsNotNone(server_name)

    def test_delete_full_modules(self):
        playbook = self.get_ansible_delete_output_from_file(copy.deepcopy(self.DEFAULT_TEMPLATE),
                                                  template_filename='examples/tosca-server-example-scalable.yaml')
        self.assertIsNotNone(playbook[0]['tasks'][0]['include_vars'])
        self.assertIsNotNone(playbook[3]['tasks'][0]['file'])
        module_names= ['os_floating_ip','os_server','os_port','os_security_group',]
        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        for task in tasks:
            if task.get('name') is not None:
                for name in module_names:
                    if task.get(name) is not None:
                        if isinstance(task.get(name), dict):
                            state = task.get(name)['state']
                            self.assertEqual(state, 'absent')
                        else:
                            self.assertIsInstance(task.get(name), six.string_types)
                            self.assertTrue('{{ item }}' in task.get(name))

    def test_os_capabilities(self):
        super(TestAnsibleOpenStackOutput, self).test_os_capabilities()

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
        template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
        playbook = self.get_ansible_create_output(template)

        self.assertIsNotNone(next(iter(playbook), {}).get('tasks'))

        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        self.check_public_address(tasks, "10.100.115.15")
        self.check_private_address(tasks, "192.168.12.25")

    def test_scalable_capabilities(self):
        super(TestAnsibleOpenStackOutput, self).test_scalable_capabilities()

    def check_scalable_capabilities(self, tasks, testing_value=None):
        server_name = None
        default_instances = 2
        if testing_value:
            default_instances = testing_value.get('default_instances', default_instances)
        for task in tasks:
            if task.get(SERVER_MODULE_NAME):
                self.assertIsNotNone(task.get('with_sequence'))
                self.assertIsNotNone(task[SERVER_MODULE_NAME].get('name'))
                self.assertTrue(task['with_sequence'], 'start=1 end=' + str(default_instances) + ' format=')
                server_name = task[SERVER_MODULE_NAME]['name']
        self.assertIsNotNone(server_name)

    def test_host_of_software_component(self):
        super(TestAnsibleOpenStackOutput, self).test_host_of_software_component()

    def check_host_of_software_component(self, playbook):
        self.assertEqual(len(playbook), 4)
        for play in playbook:
            self.assertIsNotNone(play.get('tasks'))

        self.assertEqual(playbook[3].get('hosts'), self.NODE_NAME + '_server_public_address')
        tasks2 = playbook[3]['tasks']
        tasks1 = playbook[0]['tasks'] + playbook[1]['tasks'] + playbook[2]['tasks']
        tasks = tasks1
        checked = False
        for i in range(len(tasks)):
            if tasks[i].get('os_floating_ip', None) != None:
                fip_var = tasks[i]['register']

                self.assertIsNotNone(tasks[i + 1].get('set_fact', {}).get('ansible_user'))
                self.assertIsNotNone(tasks[i + 2].get('set_fact', None))
                self.assertEqual(tasks[i + 2]['set_fact'].get('host_ip', None),
                                 '{{ host_ip | default([]) + [[ "tosca_server_example_public_address_" + item, ' +
                                 fip_var + '.results[item | int - 1].floating_ip.floating_ip_address ]] }}')

                self.assertEqual(tasks[i + 3].get('set_fact', {}).get('group'), self.NODE_NAME + '_server_public_address')
                self.assertIsNotNone(tasks[i + 4].get('include', None))
                self.assertEqual(tasks[i + 4]['include'], '/tmp/clouni/test/artifacts/add_host.yaml')
                checked = True
        self.assertTrue(checked)

        tasks = tasks2
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].get('set_fact', {}).get('version', None), 0.1)
        self.assertEqual(tasks[1].get('include', None), "/tmp/clouni/test/artifacts/examples/ansible-server-example.yaml")

    def test_get_input(self):
        super(TestAnsibleOpenStackOutput, self).test_get_input()

    def check_get_input(self, tasks, testing_value=None):
        checked = False
        for task in tasks:
            if re.match('{{ public_address_[0-9]+ }}', task.get('os_floating_ip', {}).get('floating_ip_address', '')):
                checked = True
        self.assertTrue(checked)

    def test_get_property(self):
        super(TestAnsibleOpenStackOutput, self).test_get_property()

    def check_get_property(self, tasks, testing_value=None):
        checked = True
        for task in tasks:
            os_server_task = task.get('os_server', None)
            if os_server_task != None and os_server_task.get('meta', None) != testing_value:
                checked = False
        self.assertTrue(checked)

    @unittest.skip
    def test_get_attribute(self):
        super(TestAnsibleOpenStackOutput, self).test_get_attribute()

    def check_get_attribute(self, tasks, testing_value=None):
        checked = True
        for task in tasks:
            os_server_task = task.get('os_server', None)
            if os_server_task != None and os_server_task.get('meta', None) != testing_value:
                checked = False
        self.assertTrue(checked)

    @unittest.skip
    def test_outputs(self):
        super(TestAnsibleOpenStackOutput, self).test_outputs()

    def check_outputs(self, tasks, testing_value=None):
        register_var = None
        checked = False
        for task in tasks:
            if task.get('os_floating_ip') is not None:
                register_var = task.get('register')
                self.assertIsNotNone(register_var)
            if task.get('set_fact', {}).get('server_address') is not None:
                checked = True
                self.assertEqual(task['set_fact']['server_address'], '{{ %s.floating_ip_address }}' % register_var)
        self.assertTrue(checked)

    def test_ansible_facts_in_provider_template(self):
        super(TestAnsibleOpenStackOutput, self).test_ansible_facts_in_provider_template()

    def test_tasks_success(self):
        super(TestAnsibleOpenStackOutput, self).test_tasks_success()

    def check_tasks_success(self, tasks):
        correct = True

        with open(os.path.join(utils.get_tmp_clouni_dir(), SUCCESS_CHECK_FILE), "r") as check:
            succ_tasks = yaml.load(check, Loader=Loader)
            self.assertEqual(len(tasks), len(succ_tasks))
            for task in tasks:
                if task not in succ_tasks:
                    correct = False
        self.assertTrue(correct)

    def test_host_ip_parameter(self):
        super(TestAnsibleOpenStackOutput, self).test_host_ip_parameter()

    def check_host_ip_parameter(self, playbook, testing_value):
        self.assertEqual(len(playbook), 4)
        for play in playbook:
            self.assertIsNotNone(play.get('tasks'))
            self.assertEqual(play.get('hosts'), 'localhost')

        tasks = []
        for play in playbook:
            tasks.extend(play['tasks'])
        for i in range(len(tasks)):
            if tasks[i].get('os_server'):
                self.assertEqual(tasks[i]['os_server']['nics'][0]['net-name'], testing_value)
                ansible_user = tasks[i + 1].get('set_fact', {}).get('ansible_user')
                host_ip = tasks[i + 2].get('set_fact', {}).get('host_ip')
                group = tasks[i + 3].get('set_fact', {}).get('group')
                include = tasks[i + 4].get('include')
                self.assertEqual(ansible_user, 'cirros')
                self.assertEqual(host_ip, '{{ host_ip | default([]) + [[ "tosca_server_example_private_address_" + item, tosca_server_example_server.results[item | int - 1].server.public_v4 ]] }}')
                self.assertEqual(group, 'tosca_server_example_server_private_address')
                self.assertEqual(include, '/tmp/clouni/test/artifacts/add_host.yaml')

    def check_ansible_facts_in_provider_template(self, playbook, flavor, image):
        self.assertEqual(len(playbook), 2)
        for play in playbook:
            self.assertIsNotNone(play.get('tasks'))
            self.assertEqual(play.get('hosts'), 'localhost')

        tasks = []
        for play in playbook:
            tasks.extend(play['tasks'])
        checked = False
        for task in tasks:
            if task.get('os_server'):
                checked = True
                self.assertIsNotNone(task['os_server'].get('flavor'))
                self.assertIsNotNone(task['os_server'].get('image'))
                self.assertEqual(task['os_server']['flavor'], flavor)
                self.assertEqual(task['os_server']['image'], image)
        self.assertTrue(checked)

    def test_nodes_interfaces_operations(self):
        super(TestAnsibleOpenStackOutput, self).test_nodes_interfaces_operations()

    def check_nodes_interfaces_operations(self, plays, testing_value):
        self.assertEqual(len(plays), 6)

        for play in plays:
            self.assertIsNotNone(play.get('tasks'))
            self.assertEqual(play.get('hosts'), 'localhost')

        self.assertTrue('create' in plays[1].get('name'))
        self.assertTrue('configure' in plays[2].get('name'))
        self.assertTrue('start' in plays[3].get('name'))
        self.assertTrue('stop' in plays[4].get('name'))

        checked = False
        for task in plays[1]['tasks']:
            if task.get('os_server'):
                checked = True
        self.assertTrue(checked)

        for i in range(2, 5):
            self.assertEqual(plays[i]['tasks'][0].get('set_fact', {}).get(testing_value), testing_value)
            self.assertEqual(plays[i]['tasks'][1].get('include'), '/tmp/clouni/test/artifacts/examples/ansible-operation-example.yaml')

        checked = False
        for task in plays[5]['tasks']:
            if task.get('os_floating_ip'):
                checked = True
        self.assertTrue(checked)

    def test_relationships_interfaces_operations(self):
        super(TestAnsibleOpenStackOutput, self).test_relationships_interfaces_operations()

    def check_relationships_interfaces_operations(self, plays, rel_name, soft_name, testing_value):
        self.assertEqual(len(plays), 11)
        for play in plays:
            self.assertIsNotNone(play.get('tasks'))

        self.assertTrue('create' in plays[0].get('name'))
        self.assertTrue('create' in plays[1].get('name'))

        checked = False
        for task in plays[1]['tasks']:
            if task.get('os_server'):
                checked = True
        self.assertTrue(checked)

        self.assertTrue('pre_configure_target' in plays[2].get('name'))
        self.assertTrue(rel_name + '_hosted_on' in plays[2].get('name'))
        self.assertEqual(plays[2].get('hosts'), 'localhost')

        self.assertTrue('configure' in plays[3].get('name'))

        self.assertTrue('post_configure_target' in plays[4].get('name'))
        self.assertTrue(rel_name + '_hosted_on' in plays[4].get('name'))
        self.assertEqual(plays[4].get('hosts'), 'localhost')

        checked = False
        for task in plays[5]['tasks']:
            if task.get('os_floating_ip'):
                checked = True
        self.assertTrue(checked)

        self.assertTrue('create' in plays[6].get('name'))
        self.assertTrue(soft_name + '_server_example' in plays[6].get('name'))

        if 'pre_configure_source' in plays[7].get('name'):
            self.assertTrue(rel_name+ '_hosted_on' in plays[7].get('name'))
            self.assertEqual(plays[7].get('hosts'), 'tosca_server_example_server_public_address')

            self.assertTrue('add_source' in plays[8].get('name'))
            self.assertTrue(rel_name + '_hosted_on' in plays[8].get('name'))
            self.assertEqual(plays[8].get('hosts'), 'localhost')
        elif 'add_source' in plays[7].get('name'):
            self.assertTrue(rel_name + '_hosted_on' in plays[7].get('name'))
            self.assertEqual(plays[7].get('hosts'), 'localhost')

            self.assertTrue('pre_configure_source' in plays[8].get('name'))
            self.assertTrue(rel_name + '_hosted_on' in plays[8].get('name'))
            self.assertEqual(plays[8].get('hosts'), 'tosca_server_example_server_public_address')
        else:
            self.assertTrue(False)

        self.assertTrue('configure' in plays[9].get('name'))
        self.assertTrue(soft_name+ '_server_example' in plays[9].get('name'))

        self.assertTrue('post_configure_source' in plays[10].get('name'))
        self.assertTrue(rel_name + '_hosted_on' in plays[10].get('name'))
        self.assertEqual(plays[10].get('hosts'), 'tosca_server_example_server_public_address')


        for i in list(range(2, 5)) + list(range(6, 11)):
            self.assertEqual(plays[i]['tasks'][0].get('set_fact', {}).get(testing_value), testing_value)
            self.assertEqual(plays[i]['tasks'][1].get('include'), '/tmp/clouni/test/artifacts/examples/ansible-operation-example.yaml')
