from toscatranslator.common.translator_to_ansible import translate as common_translate
import os
import yaml


class TestAnsibleProviderOutput ():
    TESTING_TEMPLATE_FILENAME = 'examples/testing-example.yaml'
    DEFAULT_TEMPLATE = {
        "tosca_definitions_version": "tosca_simple_yaml_1_0",
        "imports": [
            "toscatranslator/common/TOSCA_definition_1_0.yaml"
        ],
        "topology_template": {
            "node_templates": {
                "server_master": {
                    "type": "tosca.nodes.Compute"
                }
            }
        }
    }
    PROVIDERS = ['openstack', 'amazon']
    NODE_NAME = 'server_master'

    def write_template(self, template, filename=None):
        if not filename:
            filename = self.TESTING_TEMPLATE_FILENAME
        with open(filename, 'w') as f:
            f.write(template)

    def delete_template(self, filename=None):
        if not filename:
            filename = self.TESTING_TEMPLATE_FILENAME
        if os.path.exists(filename):
            os.remove(filename)

    def parse_yaml(self, content):
        r = yaml.load(content)
        return r

    def prepare_yaml(self, content):
        r = yaml.dump(content)
        return r

    def test_provider(self):
        assert self.PROVIDER is not None
        assert self.PROVIDER in self.PROVIDERS

    def get_ansible_output(self, template = None, template_filename = None):
        if not template:
            template = self.DEFAULT_TEMPLATE
        if not template_filename:
            template_filename = self.TESTING_TEMPLATE_FILENAME
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, {})
        print(r)
        self.delete_template(template_filename)
        playbook = self.parse_yaml(r)
        return playbook

