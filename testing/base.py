from toscatranslator.common.translator_to_configuration_dsl import translate as common_translate
from toscatranslator import shell
import os
import yaml
import copy
import difflib

from toscatranslator.common.utils import deep_update_dict
from toscatranslator.common.tosca_reserved_keys import PROVIDERS, ANSIBLE, TYPE, \
    TOSCA_DEFINITIONS_VERSION, ATTRIBUTES, PROPERTIES, CAPABILITIES, REQUIREMENTS, TOPOLOGY_TEMPLATE, NODE_TEMPLATES

TEST = 'test'


class BaseAnsibleProvider:
    TESTING_TEMPLATE_FILENAME_TO_JOIN = ['examples', 'testing-example.yaml']
    NODE_NAME = 'server_kube_master'
    DEFAULT_TEMPLATE = {
        TOSCA_DEFINITIONS_VERSION: "tosca_simple_yaml_1_0",
        TOPOLOGY_TEMPLATE: {
            NODE_TEMPLATES: {
                NODE_NAME: {
                    TYPE: "tosca.nodes.Compute"
                }
            }
        }
    }

    def testing_template_filename(self):
        r = None
        for i in self.TESTING_TEMPLATE_FILENAME_TO_JOIN:
            if r == None:
                r = i
            else:
                r = os.path.join(r, i)
        return r

    def read_template(self, filename=None):
        if not filename:
            filename = self.testing_template_filename()
        with open(filename, 'r') as f:
            return f.read()

    def write_template(self, template, filename=None):
        if not filename:
            filename = self.testing_template_filename()
        with open(filename, 'w') as f:
            f.write(template)

    def delete_template(self, filename=None):
        if not filename:
            filename = self.testing_template_filename()
        if os.path.exists(filename):
            os.remove(filename)

    def parse_yaml(self, content):
        r = yaml.load(content)
        return r

    def parse_all_yaml(self, content):
        r = yaml.full_load_all(content)
        return r

    def prepare_yaml(self, content):
        r = yaml.dump(content)
        return r

    def test_provider(self):
        assert hasattr(self, 'PROVIDER') is not None
        assert self.PROVIDER in PROVIDERS

    def get_ansible_create_output(self, template, template_filename=None, extra=None):
        if not template_filename:
            template_filename = self.testing_template_filename()
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE, TEST, False, extra=extra)
        print(r)
        self.delete_template(template_filename)
        playbook = self.parse_yaml(r)
        return playbook

    def get_ansible_delete_output(self, template, template_filename=None, extra=None):
        if not template_filename:
            template_filename = self.testing_template_filename()
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE, TEST, True, extra=extra)
        print(r)
        self.delete_template(template_filename)
        playbook = self.parse_yaml(r)
        return playbook

    def get_ansible_delete_output_from_file(self, template, template_filename=None, extra=None):
        if not template_filename:
            template_filename = self.testing_template_filename()
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE, TEST, True, extra=extra)
        print(r)
        playbook = self.parse_yaml(r)
        return playbook

    def get_k8s_output(self, template, template_filename=None):
        if not template_filename:
            template_filename = self.testing_template_filename()
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, 'kubernetes', TEST, False)
        print(r)
        manifest = list(self.parse_all_yaml(r))
        return manifest

    def update_node_template(self, template, node_name, update_value, param_type):
        update_value = {
            TOPOLOGY_TEMPLATE: {
                NODE_TEMPLATES: {
                    node_name: {
                        param_type: update_value
                    }
                }
            }
        }
        return deep_update_dict(template, update_value)

    def update_template_property(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, PROPERTIES)

    def update_template_attribute(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, ATTRIBUTES)

    def update_template_capability(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, CAPABILITIES)

    def update_template_capability_properties(self, template, node_name, capability_name, update_value):
        uupdate_value = {
            capability_name: {
                PROPERTIES: update_value
            }
        }
        return self.update_template_capability(template, node_name, uupdate_value)

    def update_template_capability_attributes(self, template, node_name, capability_name, update_value):
        uupdate_value = {
            capability_name: {
                ATTRIBUTES: update_value
            }
        }
        return self.update_node_template(template, node_name, uupdate_value, CAPABILITIES)

    def update_template_requirement(self, template, node_name, update_value):
        return self.update_node_template(template, node_name, update_value, REQUIREMENTS)

    def diff_files(self, file_name1, file_name2):
        with open(file_name1, 'r') as file1, open(file_name2, 'r') as file2:
            text1 = file1.readlines()
            text2 = file2.readlines()
            for line in difflib.unified_diff(text1, text2):
                print(line)


class TestAnsibleProvider(BaseAnsibleProvider):
    def test_full_translating(self):
        file_path = os.path.join('examples', 'tosca-server-example.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--cluster-name', 'test'])

    def test_meta(self, extra=None):
        if hasattr(self, 'check_meta'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "master=true"
            testing_parameter = {
                "meta": testing_value
            }
            template = self.update_template_property(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template, extra=extra)

            assert next(iter(playbook), {}).get('tasks')
            tasks = playbook[0]['tasks']

            if extra:
                self.check_meta(tasks, testing_value=testing_value, extra=extra)
            else:
                self.check_meta(tasks, testing_value=testing_value)

            playbook = self.get_ansible_delete_output(template, extra=extra)


    def test_private_address(self):
        if hasattr(self, 'check_private_address'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "192.168.12.26"
            testing_parameter = {
                "private_address": testing_value
            }
            template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')
            tasks = playbook[0]['tasks']

            self.check_private_address(tasks, testing_value)

    def test_public_address(self):
        if hasattr(self, 'check_public_address'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "10.10.18.217"
            testing_parameter = {
                "public_address": testing_value
            }
            template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_public_address(tasks, testing_value)

    def test_network_name(self):
        if hasattr(self, 'check_network_name'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_value = "test-two-routers"
            testing_parameter = {
                "networks": {
                    "default": {
                        "network_name": testing_value
                    }
                }
            }
            template = self.update_template_attribute(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_network_name(tasks, testing_value)

    def test_host_capabilities(self):
        if hasattr(self, 'check_host_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "num_cpus": 1,
                "disk_size": "5 GiB",
                "mem_size": "1024 MiB"
            }
            template = self.update_template_capability_properties(template, self.NODE_NAME, "host", testing_parameter)
            playbook = self.get_ansible_create_output(template)

            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_host_capabilities(tasks)

    def test_endpoint_capabilities(self):
        if hasattr(self, 'check_endpoint_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "endpoint": {
                    "properties": {
                        "protocol": "tcp",
                        "port": 22,
                        "initiator": "target"
                    },
                    "attributes": {
                        "ip_address": "0.0.0.0"
                    }
                }
            }
            template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
            playbook = self.get_ansible_create_output(template)
            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_endpoint_capabilities(tasks)

    def test_os_capabilities(self):
        if hasattr(self, 'check_os_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "architecture": "x86_64",
                "type": "ubuntu",
                "distribution": "xenial",
                "version": 16.04
            }
            template = self.update_template_capability_properties(template, self.NODE_NAME, "os", testing_parameter)
            playbook = self.get_ansible_create_output(template)
            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_os_capabilities(tasks)

    def test_scalable_capabilities(self):
        if hasattr(self, 'check_scalable_capabilities'):
            template = copy.deepcopy(self.DEFAULT_TEMPLATE)
            testing_parameter = {
                "min_instances": 1,
                "default_instances": 2,
                "max_instances": 2
            }
            template = self.update_template_capability_properties(template, self.NODE_NAME, "scalable",
                                                                  testing_parameter)
            playbook = self.get_ansible_create_output(template)
            assert next(iter(playbook), {}).get('tasks')

            tasks = playbook[0]['tasks']
            self.check_scalable_capabilities(tasks)
