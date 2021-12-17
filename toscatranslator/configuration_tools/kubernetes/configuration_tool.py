import yaml

from toscatranslator.configuration_tools.common.configuration_tool import ConfigurationTool
from toscatranslator.common.tosca_reserved_keys import KUBERNETES, PROPERTIES

API_VERSION = 'apiVersion'
API_GROUP = 'apiGroup'
KIND = 'kind'
TYPE = 'type'


class KubernetesConfigurationTool(ConfigurationTool):
    TOOL_NAME = KUBERNETES

    def to_dsl(self, provider, nodes_relationships_queue, cluster_name, is_delete, artifacts=None,
               target_directory=None, inputs=None, outputs=None, extra=None):
        if not is_delete:
            return self.to_dsl_for_create(provider, nodes_relationships_queue, artifacts, target_directory,
                                          cluster_name, extra)

    def to_dsl_for_create(self, provider, nodes_queue, artifacts, target_directory, cluster_name, extra=None):
        k8s_list = []
        for node in nodes_queue:
            k8s_list.append(self.get_k8s_kind_for_create(node))
        return yaml.dump_all(k8s_list)

    def get_k8s_kind_for_create(self, node_k8s):
        props_dict = dict()
        node = node_k8s.tmpl
        props_dict.update({KIND: node.get(TYPE).split('.')[2]})
        api = node.get(PROPERTIES, {}).get(API_GROUP, '') + '/' + node.get(PROPERTIES, {}).get(API_VERSION, '') \
            if (node.get(PROPERTIES).get(API_GROUP, '') != '') else node.get(PROPERTIES).get(API_VERSION, '')
        props_dict.update({API_VERSION: api})
        [props_dict.update({prop_name: prop}) for prop_name,prop in node.get(PROPERTIES, {}).items()
         if prop_name != API_VERSION and prop_name != API_GROUP]
        if props_dict.get('kind') == 'Deployment':
            for i in range(len(props_dict.get('spec', {}).get('template', {}).get('spec', {}).get('containers', []))):
                memory = props_dict['spec']['template']['spec']['containers'][i]\
                    .get('resources', {}).get('limits', {}).get('memory')
                if memory is not None:
                    props_dict['spec']['template']['spec']['containers'][i]['resources']['limits']['memory'] = \
                        props_dict['spec']['template']['spec']['containers'][i]['resources']['limits']['memory']\
                            .replace('MB', 'M')
        return props_dict

    def copy_conditions_to_the_directory(self, used_conditions_set, directory):
        return

    def get_artifact_extension(self):
        return '.yaml'