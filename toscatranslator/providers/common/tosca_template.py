import json

from toscaparser.common.exception import ExceptionCollector

from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider

from toscatranslator.common.exception import UnsupportedNodeTypeError

from toscatranslator.providers.common.nodefilter import ProviderNodeFilter
from toscatranslator.providers.common.provider_resource import ProviderResource

from toscatranslator import tosca_type


class ProviderToscaTemplate (object):
    def __init__(self, tosca_parser_template, facts):
        assert self.definition_file is not None
        assert self.TYPE_FACTS is not None
        assert self.TYPE_NODES is not None
        assert self.PROVIDER is not None

        self.tosca_parser_template = tosca_parser_template  # toscaparser.tosca_template:ToscaTemplate
        yaml_dict_tpl = translate_to_provider(self.PROVIDER, self.tosca_parser_template, facts, self.definition_file)
        print(json.dumps(yaml_dict_tpl))

        self.extended_facts = self.extend_facts(facts)
        ProviderNodeFilter.facts = self.extended_facts
        self.resolve_in_template_dependencies()
        self.ansible_playbook = ''
        self.ansible_playbook_ready = False
        self.provider_nodes_by_priority = dict()
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
            self.provider_nodes_by_priority[i] = []
        self.provider_nodes = self._provider_nodes()
        self.provider_nodes_by_priority = self._sort_nodes_by_priority()

    def _provider_nodes(self):
        provider_nodes = list()
        for node in self.nodetemplates:
            (namespace, category, type_name) = tosca_type.parse(node.type)
            if namespace != self.provider or category != 'nodes':
                ExceptionCollector.appendException(Exception('Unexpected values'))
            provider_node_class = self.get_node(type_name)
            if provider_node_class:
                instance = provider_node_class(node)
                provider_nodes.append(instance)
            else:
                ExceptionCollector.appendException(UnsupportedNodeTypeError(node.type))
        return provider_nodes

    def get_node(self, type_name):
        return self.TYPE_NODES.get(type_name)

    def to_ansible(self):
        nodes_queue = self.sort_nodes_by_dependency()
        for node in nodes_queue:
            self.ansible_playbook += node.to_ansible() + '\n'
        self.ansible_playbook += '\n'
        self.ansible_playbook_ready = True
        return self.ansible_playbook

    def _sort_nodes_by_priority(self):
        sorted_by_priority = dict()
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
            sorted_by_priority[i] = []
        for node in self.provider_nodes:
            sorted_by_priority[node.PRIORITY].append(node)
        return sorted_by_priority

    def sort_nodes_by_dependency(self):
        # TODO by capability dependency
        nodes = []
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
            nodes.extend(self.provider_nodes_by_priority[i])
        return nodes

    def extend_facts(self, facts):
        """
        Add some nodes to facts if they are created during script
        :param facts: existing facts
        :return:
        """
        # NOTE: optimize this part in future, searching by param, tradeoff between cpu and ram ( N * O(k) vs N * O(1) )
        new_facts = dict(
            flavors=[],
            images=[],
            networks=[],
            ports=[],
            servers=[],
            subnets=[]
        )
        for node in self.nodetemplates:
            (_, _, type_name) = tosca_type.parse(node.type)
            if type_name in self.TYPE_FACTS:
                fact_name = type_name.lower() + 's'
                caps = node.entity_tpl.get('capabilities')
                cap = caps.get('self')
                fact = cap.get('properties')
                new_facts[fact_name].append(fact)

        for k, v in new_facts.items():
            for i in v:
                facts[k].append(i)
        return facts

    def resolve_in_template_dependencies(self):
        for node in self.nodetemplates:
            for req in node.requirements:
                for k, v in req.items():
                    if type(v) is str:
                        nodetemplate = node.templates.get(v)
                        node_filter = dict()
                        properties = nodetemplate.get('properties')
                        capabilities = nodetemplate.get('capabilities')
                        if properties:
                            node_filter['properties'] = properties
                        if capabilities:
                            node_filter['capabilities'] = capabilities
                        req[k] = dict(
                            node_filter=node_filter
                        )
