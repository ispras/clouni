import os
import copy
import json

from toscaparser.common.exception import ExceptionCollector

from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider

from toscatranslator.providers.common.nodefilter import ProviderNodeFilter
from toscatranslator.providers.common.provider_resource import MAX_NUM_PRIORITIES

from toscatranslator.common import tosca_type, snake_case

from toscatranslator.providers.combined.combined_facts import FACTS_BY_PROVIDER, FACT_NAME_BY_NODE_NAME
from toscaparser.imports import ImportsLoader

from toscaparser.topology_template import TopologyTemplate


class ProviderToscaTemplate (object):
    ALL_TYPES = ['imports', 'node_types', 'capability_types', 'relationship_types',
                 'data_types', 'interface_types', 'policy_types', 'group_types']
    TOSCA_ELEMENTS_MAP_FILE = 'tosca_elements_map_to_provider.json'

    def __init__(self, tosca_parser_template, facts):

        # toscaparser.tosca_template:ToscaTemplate
        self.tosca_parser_template = tosca_parser_template
        # toscaparser.topology_template:TopologyTemplate
        self.tosca_topology_template = tosca_parser_template.topology_template

        self.input_facts = facts
        self.extended_facts = None  # refactored and extended facts
        self.facts = None  # refactored input_facts

        import_definition_file = ImportsLoader([self.definition_file()], None, self.ALL_TYPES,
                                               self.tosca_topology_template.tpl)
        self.provider_defs = import_definition_file.get_custom_defs()

        # REFACTOR FACTS
        self.facts = ProviderNodeFilter.refactor_facts(facts, self.provider(), self.provider_defs)

        self.topology_template = self.translate_to_provider()

        self.node_templates = self.topology_template.nodetemplates

        self.extended_facts = None
        not_refactored_extending_facts = self._extending_facts()
        extending_facts = ProviderNodeFilter.refactor_facts(not_refactored_extending_facts, self.provider(),
                                                            self.provider_defs)
        self.extend_facts(extending_facts)  # fulfill self.extended_facts

        ProviderNodeFilter.facts = self.extended_facts
        self.resolve_in_template_dependencies()

        self.ansible_role = None
        self.ansible_role_ready = None
        self.provider_nodes_by_priority = dict()
        for i in range(0, MAX_NUM_PRIORITIES):
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
            if namespace != self.provider() or category != 'nodes':
                ExceptionCollector.appendException(Exception('Unexpected values'))
            provider_node_instance = self.provider_resource_class(node)  # Initialize ProviderResource instance
            provider_nodes.append(provider_node_instance)
        return provider_nodes

    def to_ansible_role_for_create(self):
        """
        Fulfill ansible_role with ansible_create functions from every node
        :return:
        """
        self.ansible_role = ''
        self.ansible_role_ready = False
        nodes_queue = self.sort_nodes_by_dependency()
        for node in nodes_queue:
            self.ansible_role += node.get_ansible_task_for_create() + '\n'
        self.ansible_role += '\n'
        self.ansible_role_ready = True
        return self.ansible_role

    def _sort_nodes_by_priority(self):
        """
        Every ProviderResource child class has priority which reflects in order of objects to create in ansible
        :return: dictionary with keys = priority
        """
        sorted_by_priority = dict()
        for i in range(0, MAX_NUM_PRIORITIES):
            sorted_by_priority[i] = []
        for node in self.provider_nodes:
            priority = node.node_priority_by_type()
            sorted_by_priority[priority].append(node)
        return sorted_by_priority

    def sort_nodes_by_dependency(self):
        """
        TODO Use dependency requirement between nodes of the same type, check dependency of different types
        :return: List of nodes sorted by priority
        """
        nodes = []
        for i in range(0, MAX_NUM_PRIORITIES):
            nodes.extend(self.provider_nodes_by_priority[i])
        return nodes

    def _extending_facts(self):
        """
        Make facts if nodes are created during script
        :return:
        """
        # NOTE: optimize this part in future, searching by param, tradeoff between cpu and ram ( N * O(k) vs N * O(1) )
        new_facts_key_list = FACTS_BY_PROVIDER.get(self.provider()).keys()
        new_facts = dict()
        for key in new_facts_key_list:
            new_facts[key] = []

        for node in self.node_templates:  # node is toscaparser.nodetemplate:NodeTemplate
            (_, _, type_name) = tosca_type.parse(node.type)
            fact_name = FACT_NAME_BY_NODE_NAME.get(self.provider(), {}).get(snake_case.convert(type_name))
            if fact_name:
                new_facts[fact_name].append(node.entity_tpl.get('properties'))
        return new_facts

    def extend_facts(self, facts):
        if not self.extended_facts:
            self.extended_facts = self.facts
        for k, v in facts.items():
            self.extended_facts[k] = self.extended_facts.get(k, []) + v

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

    def definition_file(self):
        assert self.FILE_DEFINITION is not None
        cur_dir = os.path.dirname(__file__)
        par_dir = os.path.dirname(cur_dir)
        file_name = os.path.join(par_dir, self.provider(), self.FILE_DEFINITION)

        return file_name

    def provider(self):
        assert self.PROVIDER is not None
        return self.PROVIDER

    def provider_resource_class(self, node):
        raise NotImplementedError()

    def tosca_elements_map_to_provider(self):
        par_dir = os.path.dirname(os.path.dirname(__file__))
        map_file = os.path.join(par_dir, self.provider(), self.TOSCA_ELEMENTS_MAP_FILE)
        with open(map_file, 'r') as file_obj:
            data = file_obj.read()
            data_dict = json.loads(data)
            return data_dict

    def translate_to_provider(self):
        new_node_templates = translate_to_provider(self.tosca_elements_map_to_provider(),
                                                   self.tosca_topology_template.nodetemplates, self.facts)

        dict_tpl = copy.deepcopy(self.tosca_topology_template.tpl)
        dict_tpl['node_templates'] = new_node_templates

        rel_types = []
        for k, v in self.provider_defs.items():
            (_, element_type, _) = tosca_type.parse(k)
            if element_type == 'relationship_types':
                rel_types.append(v)
        topology_tpl = TopologyTemplate(dict_tpl, self.provider_defs, rel_types)

        return topology_tpl

