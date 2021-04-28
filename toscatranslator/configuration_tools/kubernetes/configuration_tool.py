import yaml

from toscatranslator.configuration_tools.common.configuration_tool import ConfigurationTool
from toscatranslator.common.tosca_reserved_keys import KUBERNETES

API_VERSION = 'apiVersion'
API_GROUP = 'apiGroup'
KIND = 'kind'
TYPE = 'type'


class KubernetesConfigurationTool(ConfigurationTool):
    TOOL_NAME = KUBERNETES

    def to_dsl_for_create(self, provider, nodes_queue, artifacts, target_directory, cluster_name, extra=None):
        k8s_list = []
        for node in nodes_queue:
            k8s_list.append(self.get_k8s_kind_for_create(node))
        return yaml.dump_all(k8s_list)

    def get_k8s_kind_for_create(self, node_k8s):
        props_dict = dict()
        node = node_k8s.nodetemplate
        props_dict.update({KIND: node.entity_tpl.get(TYPE).split('.')[2]})
        api = node.get_property_value(API_GROUP) + '/' + node.get_property_value(API_VERSION) \
            if (node.get_property_value(API_GROUP) != '') else node.get_property_value(API_VERSION)
        props_dict.update({API_VERSION: api})
        [props_dict.update({prop.name: prop.value}) for prop in node.get_properties_objects()
         if prop.name != API_VERSION and prop.name != API_GROUP]
        return props_dict

    def copy_conditions_to_the_directory(self, used_conditions_set, directory):
        return

    def get_artifact_extension(self):
        return '.yaml'