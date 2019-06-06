import json

from toscaparser.common.exception import ExceptionCollector

from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider

from toscatranslator.common.exception import UnsupportedNodeTypeError

from toscatranslator.providers.common.nodefilter import ProviderNodeFilter
from toscatranslator.providers.common.provider_resource import ProviderResource

from toscatranslator import tosca_type

from toscatranslator.providers.combined.combined_facts import FACTS_BY_PROVIDER, FACT_NAME_BY_NODE_NAME
from toscaparser.imports import ImportsLoader


class ProviderToscaTemplate (object):
    ALL_TYPES = ['imports', 'node_types', 'capability_types', 'relationship_types',
                 'data_types', 'interface_types', 'policy_types', 'group_types']

    def __init__(self, tosca_parser_template, facts):
        assert self.definition_file is not None
        assert self.TYPE_NODES is not None
        assert self.PROVIDER is not None

        ProviderResource.PROVIDER = self.PROVIDER

        # toscaparser.tosca_template:ToscaTemplate
        self.tosca_parser_template = tosca_parser_template
        # toscaparser.topology_template:TopologyTemplate
        self.tosca_topology_template = tosca_parser_template.topology_template

        self.input_facts = facts
        self.extended_facts = None  # refactored and extended facts
        self.facts = None  # refactored input_facts
        # REFACTOR FACTS
        self.facts = ProviderNodeFilter.refactor_facts(facts)

        import_definition_file = ImportsLoader([self.definition_file], None, self.ALL_TYPES,
                                               self.tosca_topology_template.tpl)
        self.provider_defs = import_definition_file.get_custom_defs()

        self.topology_template = translate_to_provider(self.PROVIDER, self.tosca_topology_template, self.facts,
                                                       self.provider_defs)
        self.node_templates = self.topology_template.nodetemplates

        self.extended_facts = None
        not_refactored_extending_facts = self._extending_facts()
        extending_facts = ProviderNodeFilter.refactor_facts(not_refactored_extending_facts)
        self.extend_facts(extending_facts)  # fulfill self.extended_facts

        ProviderNodeFilter.facts = self.extended_facts
        self.resolve_in_template_dependencies()

        self.ansible_role = ''
        self.ansible_role_ready = False
        self.provider_nodes_by_priority = dict()
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
            self.provider_nodes_by_priority[i] = []

        self.provider_nodes = self._provider_nodes()
        self.provider_nodes_by_priority = self._sort_nodes_by_priority()

    def _provider_nodes(self):
        """
        Create a list of ProviderResource classes to represent a node in TOSCA
        :return: list of class objects inherited from ProbiderResource
        """
        provider_nodes = list()
        for node in self.node_templates:
            (namespace, category, type_name) = tosca_type.parse(node.type)
            if namespace != self.PROVIDER or category != 'nodes':
                ExceptionCollector.appendException(Exception('Unexpected values'))
            provider_node_class = self.get_node(type_name)
            if provider_node_class:
                instance = provider_node_class(node)  # Initialize ProviderResource instance
                provider_nodes.append(instance)
            else:
                ExceptionCollector.appendException(UnsupportedNodeTypeError(node.type))
        return provider_nodes

    def get_node(self, type_name):
        """
        Find a class inherited from ProviderResource by name
        :param type_name: class type object
        :return:
        """
        return self.TYPE_NODES.get(type_name)

    def to_ansible_role_for_create(self):
        """
        Fulfill ansible_role with ansible_create functions from every node
        :return:
        """
        nodes_queue = self.sort_nodes_by_dependency()
        for node in nodes_queue:
            self.ansible_role += node.to_ansible_task_for_create() + '\n'
        self.ansible_role += '\n'
        self.ansible_role_ready = True
        return self.ansible_role

    def _sort_nodes_by_priority(self):
        """
        Every ProviderResource child class has PRIORITY which reflects in order of objects to create in ansible
        :return: dictionary with keys = PRIORITY
        """
        sorted_by_priority = dict()
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
            sorted_by_priority[i] = []
        for node in self.provider_nodes:
            sorted_by_priority[node.PRIORITY].append(node)
        return sorted_by_priority

    def sort_nodes_by_dependency(self):
        """
        TODO Use dependency requirement between nodes of the same type, check dependency of different types
        :return: List of nodes sorted by PRIORITY
        """
        nodes = []
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
            nodes.extend(self.provider_nodes_by_priority[i])
        return nodes

    def _extending_facts(self):
        """
        Make facts if nodes are created during script
        :return:
        """
        # NOTE: optimize this part in future, searching by param, tradeoff between cpu and ram ( N * O(k) vs N * O(1) )
        new_facts_key_list = FACTS_BY_PROVIDER.get(self.PROVIDER).keys()
        new_facts = dict()
        for key in new_facts_key_list:
            new_facts[key] = []

        for node in self.node_templates:  # node is toscaparser.nodetemplate:NodeTemplate
            (_, _, type_name) = tosca_type.parse(node.type)
            fact_name = FACT_NAME_BY_NODE_NAME.get(self.PROVIDER, {}).get(type_name.lower())
            if fact_name:
                new_facts[fact_name].append(node.entity_tpl.get('properties'))
        return new_facts

    def extend_facts(self, facts):
        if not self.extended_facts:
            self.extended_facts = self.facts
        for k, v in facts.items():
            self.extended_facts[k] = self.extended_facts.get(k, []).extend(v)

    def resolve_in_template_dependencies(self):
        """
        TODO think through the logic to replace mentions by id
        Changes all mentions of node_templates by name in requirements, places dictionary with node_filter instead
        :return:
        """
        for node in self.node_templates:
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
