from toscatranslator.common.translator_to_configuration_dsl import translate as common_translate
import os
import yaml

from toscatranslator.common.utils import deep_update_dict
from toscatranslator.common.tosca_reserved_keys import PROVIDERS, ANSIBLE, TYPE, \
    IMPORTS, TOSCA_DEFINITIONS_VERSION, ATTRIBUTES, PROPERTIES, CAPABILITIES, REQUIREMENTS, TOPOLOGY_TEMPLATE, NODE_TEMPLATES


class TestAnsibleProviderOutput ():
    TESTING_TEMPLATE_FILENAME = 'examples/testing-example.yaml'
    NODE_NAME = 'server_master'
    DEFAULT_TEMPLATE = {
        TOSCA_DEFINITIONS_VERSION: "tosca_simple_yaml_1_0",
        IMPORTS: [
            "toscatranslator/common/TOSCA_definition_1_0.yaml"
        ],
        TOPOLOGY_TEMPLATE: {
            NODE_TEMPLATES: {
                NODE_NAME: {
                    TYPE: "tosca.nodes.Compute"
                }
            }
        }
    }

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
        assert self.PROVIDER in PROVIDERS

    def get_ansible_output(self, template, template_filename = None):
        if not template_filename:
            template_filename = self.TESTING_TEMPLATE_FILENAME
        self.write_template(self.prepare_yaml(template))
        r = common_translate(template_filename, False, self.PROVIDER, ANSIBLE)
        print(r)
        self.delete_template(template_filename)
        playbook = self.parse_yaml(r)
        return playbook

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

