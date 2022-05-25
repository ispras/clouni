import unittest

from testing.base import TestAnsibleProvider

import copy, os, re, yaml
from shell_clouni import shell

SERVER_MODULE_NAME = 'os_server'
PORT_MODULE_NAME = 'os_port'
FIP_MODULE_NAME = 'os_floating_ip'
SEC_GROUP_MODULE_NAME = 'os_security_group'
SEC_RULE_MODULE_NAME = 'os_security_group_rule'
NETWORK_MODULE_NAME = 'os_network'
SUBNET_MODULE_NAME = 'os_subnet'


class TestAnsibleOpenStackOutput (unittest.TestCase, TestAnsibleProvider):
    PROVIDER = 'openstack'

    def test_validation(self):
        file_path = os.path.join('examples', 'tosca-server-example-openstack.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--validate-only'])

    def test_translating_to_ansible(self):
        file_path = os.path.join('examples', 'tosca-server-example-openstack.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER])

    def test_translating_to_ansible_delete(self):
        file_path = os.path.join('examples', 'tosca-server-example-openstack.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--delete','false','--provider', self.PROVIDER])

    def test_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path])

        file_diff_path = os.path.join('examples', 'tosca-server-example-ansible-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_delete_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output-delete.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--delete',
                    '--output-file', file_output_path])

        file_diff_path = os.path.join('examples', 'tosca-server-example-ansible-delete-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_full_async_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-server-example-output-async.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--async',
                    '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1',
                    '--output-file', file_output_path])

        file_diff_path = os.path.join('examples', 'tosca-server-example-ansible-async-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_full_translating_network(self):
        file_path = os.path.join('examples', 'tosca-network-and-port-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-network-and-port-example-output.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER,
                    '--output-file', file_output_path])

        file_diff_path = os.path.join('examples', 'tosca-network-and-port-example-ansible-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_delete_full_translating_network(self):
        file_path = os.path.join('examples', 'tosca-network-and-port-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-network-and-port-example-output-delete.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--delete',
                    '--output-file', file_output_path])

        file_diff_path = os.path.join('examples', 'tosca-network-and-port-example-ansible-delete-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_full_async_translating_network(self):
        file_path = os.path.join('examples', 'tosca-network-and-port-example.yaml')
        file_output_path = os.path.join('examples', 'tosca-network-and-port-example-output-async.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--async',
                    '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1',
                    '--output-file', file_output_path])

        file_diff_path = os.path.join('examples', 'tosca-network-and-port-example-ansible-async-openstack.yaml')
        self.diff_files(file_output_path, file_diff_path)

    def test_network_with_compute(self):
        file_path = os.path.join('examples', 'tosca-network-and-server-example.yaml')
        template = self.read_template(file_path)
        playbook = self.get_ansible_create_output(template, file_path, delete_template=False)
        self.assertEqual(len(playbook), 6)
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

    def test_delete_full_async_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        shell.main(['--template-file', file_path, '--cluster-name', 'test', '--provider', self.PROVIDER, '--async',
                    '--delete', '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])

    def test_server_name(self):
        template = copy.deepcopy(self.DEFAULT_TEMPLATE)
        playbook = self.get_ansible_create_output(template)
        self.assertEqual(len(playbook), 3)
        for play in playbook:
            self.assertIsInstance(play, dict)
            self.assertIsNotNone(play['tasks'])
        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        self.assertEqual(len(tasks), 18)
        self.assertIsNotNone(tasks[2][SERVER_MODULE_NAME])
        server = tasks[2][SERVER_MODULE_NAME]
        self.assertEqual(server['name'], self.NODE_NAME)

    def test_async_meta(self):
        extra={
            'global': {
                'async': True,
                'retries': 3,
                'delay': 1,
                'poll': 0
            }
        }
        super(TestAnsibleOpenStackOutput, self).test_meta(extra=extra)

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
        self.assertIsNotNone(playbook[4]['tasks'][0]['file'])
        module_names= ['os_floating_ip','os_server','os_port','os_security_group',]
        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        for task in tasks:
            if task.get('name') is not None:
                modules = [task.get(name)['state'] for name in module_names if task.get(name) is not None]
                self.assertEqual(modules[0], 'absent')

    @unittest.skip("async will be deleted")
    def test_delete_full_modules_async(self):
        extra = {
            'global': {
                'async': True,
                'retries': 3,
                'delay': 1,
                'poll': 0
            }
        }
        playbook = self.get_ansible_delete_output_from_file(copy.deepcopy(self.DEFAULT_TEMPLATE),
                                                  template_filename='examples/tosca-server-example-scalable.yaml', extra=extra)
        self.assertIsNotNone(playbook[0]['tasks'][0]['include_vars'])
        self.assertIsNotNone(playbook[4]['tasks'][0]['file'])
        module_names = ['os_floating_ip','os_server','os_port','os_security_group']
        delete_task_counter = 0
        async_task_counter = 0
        tasks = []
        for play in playbook:
            for task in play['tasks']:
                tasks.append(task)
        for task in tasks:
            if task.get('name') is not None:
                modules = [task.get(name)['state'] for name in module_names if task.get(name) is not None]
                if modules:
                    delete_task_counter+=1
                    self.assertEqual(modules[0], 'absent')
                else:
                    async_task_counter+=1
        self.assertEqual(async_task_counter, delete_task_counter*2)

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

    def check_host_of_software_component(self, tasks1, tasks2):
        tasks = tasks1
        checked = False
        for i in range(len(tasks)):
            if tasks[i].get('os_floating_ip', None) != None:
                fip_var = tasks[i]['register']

                self.assertIsNotNone(tasks[i+1].get('set_fact', None))
                self.assertEqual(tasks[i+1]['set_fact'].get('host_ip', None),
                                 '{{ '+ fip_var + '.floating_ip.floating_ip_address }}')

                self.assertIsNotNone(tasks[i+2].get('add_host', None))
                self.assertEqual(tasks[i+2]['add_host'].get('hostname', None),
                                 '{{ host_ip }}')
                self.assertEqual(tasks[i+2]['add_host'].get('groups', None),
                                 self.NODE_NAME)

                self.assertIsNotNone(tasks[i+3].get('shell', None))
                self.assertEqual(tasks[i+3]['shell'],
                                 'ssh-keyscan {{ host_ip }},`dig +short {{ host_ip }}`')
                self.assertIsNotNone(tasks[i+3].get('register', None))
                self.assertEqual(tasks[i+3]['register'],
                                 'host_key')

                self.assertIsNotNone(tasks[i+4].get('known_hosts', None))
                self.assertEqual(tasks[i+4]['known_hosts'].get('name', None),
                                 '{{ host_ip }}')
                self.assertEqual(tasks[i+4]['known_hosts'].get('key', None),
                                 '{{ host_key.stdout }}')
                checked = True
        self.assertTrue(checked)

        tasks = tasks2
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].get('set_fact', {}).get('version', None), 0.1)
        self.assertEqual(tasks[1].get('include', None), "artifacts/ansible-server-example.yaml")

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

    def test_get_attribute(self):
        super(TestAnsibleOpenStackOutput, self).test_get_attribute()

    def check_get_attribute(self, tasks, testing_value=None):
        checked = True
        for task in tasks:
            os_server_task = task.get('os_server', None)
            if os_server_task != None and os_server_task.get('meta', None) != testing_value:
                checked = False
        self.assertTrue(checked)

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