import os
import copy
import json
import yaml
import fnmatch

from toscaparser.common.exception import ExceptionCollector

from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider

from toscatranslator.providers.common.nodefilter import ProviderNodeFilter
from toscatranslator.providers.common.provider_resource import MAX_NUM_PRIORITIES

from toscatranslator.common import tosca_type, snake_case

from toscatranslator.providers.combined.combined_facts import FACTS_BY_PROVIDER, FACT_NAME_BY_NODE_NAME
from toscaparser.imports import ImportsLoader

from toscaparser.topology_template import TopologyTemplate

from toscatranslator.configuration_tools.combined.combine_configuration_tools import CONFIGURATION_TOOLS
from toscatranslator.providers.combined.combine_provider_resources import PROVIDER_RESOURCES
from toscatranslator.common.exception import UnknownProvider, ProviderMappingFileError, TemplateDependencyError

from toscatranslator.providers.common.tosca_reserved_keys import SERVICE_TEMPLATE_KEYS, PROPERTIES, CAPABILITIES, NODES, \
    GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT, RELATIONSHIP, NODE, TEMPLATE_REFERENCES, NODE_TEMPLATES, \
    RELATIONSHIP_TYPES, NAME


class ProviderToscaTemplate (object):

    TOSCA_ELEMENTS_MAP_FILE = 'tosca_elements_map_to_%(provider)s.*'
    FILE_DEFINITION = 'TOSCA_%(provider)s_definition_1_0.yaml'
    DEPENDENCY_FUNCTIONS = (GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT)

    def __init__(self, tosca_parser_template, facts, provider):

        self.provider = provider
        # toscaparser.tosca_template:ToscaTemplate
        self.tosca_parser_template = tosca_parser_template
        # toscaparser.topology_template:TopologyTemplate
        self.tosca_topology_template = tosca_parser_template.topology_template

        self.input_facts = facts
        self.extended_facts = None  # refactored and extended facts
        self.facts = None  # refactored input_facts

        import_definition_file = ImportsLoader([self.definition_file()], None, list(SERVICE_TEMPLATE_KEYS),
                                               self.tosca_topology_template.tpl)
        self.provider_defs = import_definition_file.get_custom_defs()

        self.artifacts = [self.definition_file()]

        # REFACTOR FACTS
        self.facts = ProviderNodeFilter.refactor_facts(facts, self.provider, self.provider_defs)

        self.topology_template = self.translate_to_provider()

        self.node_templates = self.topology_template.nodetemplates
        self.relationship_templates = self.topology_template.relationship_templates

        self.extended_facts = None
        not_refactored_extending_facts = self._extending_facts()
        extending_facts = ProviderNodeFilter.refactor_facts(not_refactored_extending_facts, self.provider,
                                                            self.provider_defs)
        self.extend_facts(extending_facts)  # fulfill self.extended_facts

        ProviderNodeFilter.facts = self.extended_facts
        self.template_dependencies = dict()  # list of lists
        # After this step self.node_templates has requirements with node_filter parameter
        self.resolve_in_template_dependencies()
        self.resolve_in_template_get_functions()

        self.configuration_content = None
        self.configuration_ready = None

        self.provider_nodes = self._provider_nodes()
        self.provider_nodes_by_name = self._provider_nodes_by_name()
        self.relationship_templates_by_name = self._relationship_templates_by_name()

        # self.provider_node_names_by_priority = dict()
        # for i in range(0, MAX_NUM_PRIORITIES):
        #     self.provider_node_names_by_priority[i] = []
        self.provider_node_names_by_priority = self._sort_nodes_by_priority()
        self.provider_nodes_queue = self.sort_nodes_by_dependency()

    def _provider_nodes(self):
        """
        Create a list of ProviderResource classes to represent a node in TOSCA
        :return: list of class objects inherited from ProbiderResource
        """
        provider_nodes = list()
        for node in self.node_templates:
            (namespace, category, type_name) = tosca_type.parse(node.type)
            if namespace != self.provider or category != NODES:
                ExceptionCollector.appendException(Exception('Unexpected values'))
            provider_node_class = PROVIDER_RESOURCES.get(self.provider)
            if not provider_node_class:
                ExceptionCollector.appendException(UnknownProvider(
                    what=self.provider
                ))
            provider_node_instance = provider_node_class(node, self.relationship_templates)
            provider_nodes.append(provider_node_instance)
        return provider_nodes

    def to_configuration_dsl_for_create(self, configuration_tool):
        """
        Fulfill configuration_content with functions based on configuration tool from every node
        :return:
        """
        self.configuration_content = ''
        self.configuration_ready = False
        tool = CONFIGURATION_TOOLS.get(configuration_tool)()
        content = tool.to_dsl_for_create(self.provider, self.provider_nodes_queue)

        self.configuration_content = yaml.dump(content)
        self.configuration_ready = True
        return self.configuration_content

    def _sort_nodes_by_priority(self):
        """
        Every ProviderResource child class has priority which reflects in order of objects to create in configuration dsl
        :return: dictionary with keys = priority
        """
        sorted_by_priority = dict()
        for i in range(0, MAX_NUM_PRIORITIES):
            sorted_by_priority[i] = []
        for node in self.provider_nodes:
            priority = node.node_priority_by_type()
            sorted_by_priority[priority].append(node.nodetemplate.name)
        return sorted_by_priority

    def _relationship_templates_by_name(self):
        by_name = dict()
        for rel in self.relationship_templates:
            by_name[rel.name] = rel

        return by_name

    def _provider_nodes_by_name(self):
        """
        Get provider_nodes_by_name
        :return: self.provider_nodes_by_name
        """

        provider_nodes_by_name = dict()
        for node in self.provider_nodes:
            provider_nodes_by_name[node.nodetemplate.name] = node

        return provider_nodes_by_name

    def sort_nodes_by_dependency(self):
        """
        TODO Use dependency requirement between nodes of the same type, check dependency of different types
        :param: self.template_dependencies
        :return: List of nodes sorted by priority
        """
        template_names = []
        relation_names = list(self.relationship_templates_by_name.keys())

        for priority in range(0, MAX_NUM_PRIORITIES):
            nodes_in_priority = []
            nodes_left_next = set(self.provider_node_names_by_priority[priority])
            infinite_error = False
            while len(nodes_left_next) or infinite_error > 0:
                nodes_left = copy.copy(nodes_left_next)
                infinite_error = True
                for templ_name in nodes_left:
                    set_intersection = nodes_left_next.intersection(self.template_dependencies.get(templ_name, set()))
                    if len(set_intersection) == 0:
                        infinite_error = False
                        nodes_in_priority.append(templ_name)
                        nodes_left_next.remove(templ_name)
            if infinite_error:
                ExceptionCollector.appendException(TemplateDependencyError(
                    what="of priority " + str(priority)
                ))
            for templ_name in nodes_in_priority:
                node_dependencies = self.template_dependencies.get(templ_name, set())

                for dep_name in node_dependencies:
                    # Two cases: it's already in a list
                    #              it's a relationship
                    #              it's in priority
                    if dep_name in relation_names:
                        template_names.append(dep_name)
                    elif dep_name in template_names:
                        pass
                    else:
                        ExceptionCollector.appendException(TemplateDependencyError(
                            what=dep_name
                        ))
                template_names.append(templ_name)
            # Here we added nodes of the same priority

        templates = []
        for templ_name in template_names:
            templ = self.provider_nodes_by_name.get(templ_name, self.relationship_templates_by_name.get(templ_name))
            if templ is None:
                ExceptionCollector.appendException(TemplateDependencyError(
                    what=templ_name
                ))
            templates.append(templ)

        return templates

    def _extending_facts(self):
        """
        Make facts if nodes are created during script
        :return:
        """
        # NOTE: optimize this part in future, searching by param, tradeoff between cpu and ram ( N * O(k) vs N * O(1) )
        new_facts_key_list = FACTS_BY_PROVIDER.get(self.provider).keys()
        new_facts = dict()
        for key in new_facts_key_list:
            new_facts[key] = []

        for node in self.node_templates:  # node is toscaparser.nodetemplate:NodeTemplate
            (_, _, type_name) = tosca_type.parse(node.type)
            fact_name = FACT_NAME_BY_NODE_NAME.get(self.provider, {}).get(snake_case.convert(type_name))
            if fact_name:
                if isinstance(fact_name, list):
                    fact_name = fact_name[0]
                new_facts[fact_name].append(node.entity_tpl.get(PROPERTIES))
        return new_facts

    def extend_facts(self, facts):
        if not self.extended_facts:
            self.extended_facts = self.facts
        for k, v in facts.items():
            self.extended_facts[k] = self.extended_facts.get(k, []) + v

    def add_template_dependency(self, node_name, dependency_name):
        if self.template_dependencies.get(node_name) is None:
            self.template_dependencies[node_name] = {dependency_name}
        else:
            self.template_dependencies[node_name].add(dependency_name)

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
                        # The case when the requirement is a name of node or relationship template

                        # Store the dependencies of nodes
                        self.add_template_dependency(node.name, v)

                        nodetemplate = node.templates.get(v)
                        node_filter = dict()
                        properties = nodetemplate.get(PROPERTIES)
                        capabilities = nodetemplate.get(CAPABILITIES)
                        if properties:
                            node_filter[PROPERTIES] = properties
                        if capabilities:
                            node_filter[CAPABILITIES] = capabilities
                        req[k] = dict(
                            node_filter=node_filter
                        )
                    else:
                        # The case when requirement has parameters.
                        # Valid keys are ('node', 'node_filter', 'relationship', 'capability', 'occurrences')
                        # Only node and relationship might be a template name or a type
                        req_relationship = req[k].get(RELATIONSHIP)
                        req_node = req[k].get(NODE)

                        if req_relationship is not None:
                            _, _, type_name = tosca_type.parse(req_relationship)
                            if type_name is None:
                                self.add_template_dependency(node.name, req_relationship)

                        if req_node is not None:
                            _, _, type_name = tosca_type.parse(req_node)
                            if type_name is None:
                                self.add_template_dependency(node.name, req_node)

    def search_get_function(self, node_name, data):
        """
        Function for recursion search of object in data
        Get functions are the keys of dictionary
        :param node_name:
        :param data:
        :return:
        """
        if isinstance(data, dict):
            for k, v in data.items():
                if k not in self.DEPENDENCY_FUNCTIONS:
                    self.search_get_function(node_name, v)
                else:
                    if isinstance(v, list):
                        template_name = v[0]
                    else:
                        params = v.split(',')
                        template_name = params[0]
                    if not template_name in TEMPLATE_REFERENCES:
                        self.add_template_dependency(node_name, template_name)
        elif isinstance(data, list):
            for i in data:
                self.search_get_function(node_name, i)
        elif isinstance(data, (str, int, float)):
            return

        return

    def resolve_in_template_get_functions(self):
        """
        Search in all nodes for get function mentions and get its target name
        :return: None
        """

        for node in self.node_templates:
            self.search_get_function(node.name, node.entity_tpl)

        for rel in self.relationship_templates:
            self.search_get_function(rel.name, rel.entity_tpl)

    def definition_file(self):
        file_definition = self.FILE_DEFINITION % {'provider': self.provider}
        cur_dir = os.path.dirname(__file__)
        par_dir = os.path.dirname(cur_dir)
        file_name = os.path.join(par_dir, self.provider, file_definition)

        return file_name

    def tosca_elements_map_to_provider(self):
        tosca_elements_map_file = self.TOSCA_ELEMENTS_MAP_FILE % {'provider': self.provider}
        par_dir = os.path.dirname(os.path.dirname(__file__))
        data_dict = dict()
        is_find = False
        for file_name in os.listdir(os.path.join(par_dir, self.provider)):
            if fnmatch.fnmatch(file_name, tosca_elements_map_file + '*'):
                with open(os.path.join(par_dir, self.provider, file_name), 'r') as file_obj:
                    data = file_obj.read()
                    is_find = True
                    try:
                        if file_name.lower().endswith(('.json')):
                            data_dict = json.loads(data)
                            break
                        else:
                            data_dict = yaml.safe_load(data)
                            break
                    except:
                        continue
        if 0 == len(data_dict):
            if is_find:
                ExceptionCollector.appendException(ProviderMappingFileError(
                    what=tosca_elements_map_file
                ))
            else:
                ExceptionCollector.appendException(FileNotFoundError(
                    'Can\'t find mapping file: ' + tosca_elements_map_file + '\nPlease, check that extension is .yaml or .json')
                )
        return data_dict

    def generate_artifacts(self, new_artifacts):
        """
        From the info of new artifacts generate files which execute
        :param new_artifacts: list of dicts containing (value, source, parameters, executor, name, configuration_tool)
        :return: None
        """
        for art in new_artifacts:
            # TODO make some actions
            file_name = art[NAME]
            self.artifacts.append(file_name)
        return

    def translate_to_provider(self):
        new_node_templates, new_artifacts = translate_to_provider(self.tosca_elements_map_to_provider(),
                                                   self.tosca_topology_template.nodetemplates, self.facts)

        dict_tpl = copy.deepcopy(self.tosca_topology_template.tpl)
        dict_tpl[NODE_TEMPLATES] = new_node_templates

        rel_types = []
        for k, v in self.provider_defs.items():
            (_, element_type, _) = tosca_type.parse(k)
            if element_type == RELATIONSHIP_TYPES:
                rel_types.append(v)
        topology_tpl = TopologyTemplate(dict_tpl, self.provider_defs, rel_types)
        self.generate_artifacts(new_artifacts)

        return topology_tpl

