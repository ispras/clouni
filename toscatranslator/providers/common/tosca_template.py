import os
import copy
import json
import yaml

from toscaparser.common.exception import ExceptionCollector, ValidationError

from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider

from toscatranslator.common import tosca_type

from toscaparser.imports import ImportsLoader

from toscaparser.topology_template import TopologyTemplate

from toscatranslator.configuration_tools.combined.combine_configuration_tools import CONFIGURATION_TOOLS
from toscatranslator.common.exception import ProviderFileError, TemplateDependencyError, UnsupportedExecutorType, \
    ProviderConfigurationParameterError

from toscatranslator.common.tosca_reserved_keys import *
from toscatranslator.common.utils import deep_update_dict
from toscatranslator.providers.common.provider_resource import ProviderResource
from toscatranslator.providers.common.provider_configuration import ProviderConfiguration


class ProviderToscaTemplate(object):
    REQUIRED_CONFIG_PARAMS = (TOSCA_ELEMENTS_MAP_FILE, TOSCA_ELEMENTS_DEFINITION_FILE) = \
        ('tosca_elements_map_file', 'tosca_elements_definition_file')
    DEPENDENCY_FUNCTIONS = (GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT)
    DEFAULT_ARTIFACTS_DIRECTOR = ARTIFACTS

    def __init__(self, tosca_parser_template, provider, cluster_name):

        self.provider = provider
        self.provider_config = ProviderConfiguration(self.provider)
        self.cluster_name = cluster_name
        ExceptionCollector.start()
        for sec in self.REQUIRED_CONFIG_PARAMS:
            if not self.provider_config.config[self.provider_config.MAIN_SECTION].get(sec):
                ExceptionCollector.appendException(ProviderConfigurationParameterError(
                    what=sec
                ))
        ExceptionCollector.stop()
        if ExceptionCollector.exceptionsCaught():
            raise ValidationError(
                message='\nTranslating to provider failed: '
                    .join(ExceptionCollector.getExceptionsReport())
            )

        # toscaparser.tosca_template:ToscaTemplate
        self.tosca_parser_template = tosca_parser_template
        # toscaparser.topology_template:TopologyTemplate
        self.tosca_topology_template = tosca_parser_template.topology_template

        import_definition_file = ImportsLoader([self.definition_file()], None, list(SERVICE_TEMPLATE_KEYS),
                                               self.tosca_topology_template.tpl)
        self.full_provider_defs = copy.copy(self.tosca_topology_template.custom_defs)
        self.provider_defs = import_definition_file.get_custom_defs()
        self.full_provider_defs.update(self.provider_defs)

        self.artifacts = []
        self.used_conditions_set = set()
        self.extra_configuration_tool_params = dict()

        self.topology_template = self.translate_to_provider()

        self.node_templates = self.topology_template.nodetemplates
        self.relationship_templates = self.topology_template.relationship_templates

        self.template_dependencies = dict()  # list of lists
        # After this step self.node_templates has requirements with node_filter parameter
        self.resolve_in_template_dependencies()
        self.resolve_in_template_get_functions()

        self.configuration_content = None
        self.configuration_ready = None

        # Create the list of ProviderResource instances
        self.provider_nodes = self._provider_nodes()
        self.provider_nodes_by_name = self._provider_nodes_by_name()
        self.relationship_templates_by_name = self._relationship_templates_by_name()

        self.provider_node_names_by_priority = self._sort_nodes_by_priority()
        self.provider_nodes_queue = self.sort_nodes_by_dependency()

    def _provider_nodes(self):
        """
        Create a list of ProviderResource classes to represent a node in TOSCA
        :return: list of class objects inherited from ProviderResource
        """
        provider_nodes = list()
        for node in self.node_templates:
            (namespace, category, type_name) = tosca_type.parse(node.type)
            if namespace != self.provider or category != NODES:
                ExceptionCollector.appendException(Exception('Unexpected values'))
            provider_node_instance = ProviderResource(self.provider, node, self.relationship_templates)
            provider_nodes.append(provider_node_instance)
        return provider_nodes

    def to_configuration_dsl(self, configuration_tool, is_delete, directory=None, extra=None):
        """
        Fulfill configuration_content with functions based on configuration tool from every node
        :return:
        """
        if not directory:
            directory = self.DEFAULT_ARTIFACTS_DIRECTOR
        if not extra:
            extra = dict()

        self.configuration_content = ''
        self.configuration_ready = False
        tool = CONFIGURATION_TOOLS.get(configuration_tool)()
        if bool(self.used_conditions_set):
            tool.copy_conditions_to_the_directory(self.used_conditions_set, directory)
        tool_artifacts = []
        for art in self.artifacts:
            executor = art.get(EXECUTOR)
            if bool(executor) and executor != configuration_tool:
                self.generate_artifacts([art], directory)
            else:
                tool_artifacts.append(art)
        extra = deep_update_dict(extra, self.extra_configuration_tool_params.get(configuration_tool, {}))
        self.configuration_content = tool.to_dsl_for_delete(self.provider, self.provider_nodes_queue, tool_artifacts, directory, self.cluster_name, extra=extra) \
                if is_delete else tool.to_dsl_for_create(self.provider, self.provider_nodes_queue, tool_artifacts, directory, self.cluster_name, extra=extra)
        self.configuration_ready = True
        return self.configuration_content

    def generate_artifacts(self, new_artifacts, directory=None):
        """
        From the info of new artifacts generate files which execute
        :param new_artifacts: list of dicts containing (value, source, parameters, executor, name, configuration_tool)
        :return: None
        """
        if not directory:
            directory = self.DEFAULT_ARTIFACTS_DIRECTOR

        for art in new_artifacts:
            filename = os.path.join(directory, art[NAME])
            configuration_class = CONFIGURATION_TOOLS.get(art[EXECUTOR])()
            if not configuration_class:
                ExceptionCollector.appendException(UnsupportedExecutorType(
                    what=art[EXECUTOR]
                ))
            configuration_class.create_artifact(filename, art)
            self.artifacts.append(filename)

    def _sort_nodes_by_priority(self):
        """
        Every ProviderResource child class has priority which reflects in order of objects to create in configuration dsl

        :return: dictionary with keys = priority
        """
        sorted_by_priority = dict()
        for i in range(0, ProviderResource.MAX_NUM_PRIORITIES):
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
        Use dependency requirement between nodes of the same type, check dependency of different types
        :param self.template_dependencies
        :param self.relationship_templates_by_name
        :param self.provider_node_names_by_priority
        :param self.provider_nodes_by_name
        :return: List of nodes sorted by priority
        """
        template_names = []
        relation_names = list(self.relationship_templates_by_name.keys())

        group_by_templ_name = dict()
        group = 0
        for priority in range(0, len(self.provider_node_names_by_priority)):
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
                        group_by_templ_name[templ_name] = group
                group += 1
            # Here we added nodes of the same priority
            if infinite_error:
                ExceptionCollector.appendException(TemplateDependencyError(
                    what="of priority " + str(priority)
                ))
            for templ_name in nodes_in_priority:
                # Add relationships for every node
                node_dependencies = self.template_dependencies.get(templ_name, set())

                for dep_name in node_dependencies:
                    if dep_name in relation_names and not dep_name in template_names:
                        template_names.append(dep_name)
                    elif dep_name in template_names:
                        pass
                    else:
                        ExceptionCollector.appendException(TemplateDependencyError(
                            what=dep_name
                        ))
                template_names.append(templ_name)

        templates = []
        for templ_name in template_names:
            templ = self.provider_nodes_by_name.get(templ_name, self.relationship_templates_by_name.get(templ_name))
            if templ is None:
                ExceptionCollector.appendException(TemplateDependencyError(
                    what=templ_name
                ))
            if group_by_templ_name.get(templ_name):
                templ.dependency_order = group_by_templ_name[templ_name]
            templates.append(templ)

        return templates

    def add_template_dependency(self, node_name, dependency_name):
        if not dependency_name == SELF and not node_name == dependency_name:
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
                        props_list = []
                        if properties:
                            for prop_name, prop in properties.items():
                                props_list.append({prop_name: prop})
                        capabilities = nodetemplate.get(CAPABILITIES)
                        caps_list = []
                        if capabilities:
                            for cap_name, cap in capabilities.items():
                                cap_props = cap.get(PROPERTIES, {})
                                cap_props_list = []
                                for prop_name, prop in cap_props.items():
                                    cap_props_list.append({prop_name, prop})
                                caps_list.append({PROPERTIES: cap_props_list})

                        if properties:
                            node_filter[PROPERTIES] = props_list
                        if capabilities:
                            node_filter[CAPABILITIES] = caps_list
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
        file_definition = self.provider_config.config['main'][self.TOSCA_ELEMENTS_DEFINITION_FILE]
        if not os.path.isabs(file_definition):
            file_definition = os.path.join(self.provider_config.config_directory, file_definition)

        if not os.path.isfile(file_definition):
            ExceptionCollector.appendException(ProviderFileError(
                what=file_definition
            ))

        return file_definition

    def tosca_elements_map_to_provider(self):
        tosca_elements_map_file = self.provider_config.config['main'][self.TOSCA_ELEMENTS_MAP_FILE]
        if not os.path.isabs(tosca_elements_map_file):
            tosca_elements_map_file = os.path.join(self.provider_config.config_directory, tosca_elements_map_file)

        if not os.path.isfile(tosca_elements_map_file):
            ExceptionCollector.appendException(ProviderFileError(
                what=tosca_elements_map_file
            ))

        with open(tosca_elements_map_file, 'r') as file_obj:
            data = file_obj.read()
            data_dict = {}
            try:
                data_dict = json.loads(data)
            except:
                try:
                    data_dict = yaml.safe_load(data)
                except:
                    pass
        if 0 == len(data_dict):
            ExceptionCollector.appendException(ProviderFileError(
                what=tosca_elements_map_file
            ))
        return data_dict

    def translate_to_provider(self):
        new_element_templates, new_artifacts, conditions_set, new_extra = translate_to_provider(
            self.tosca_elements_map_to_provider(), self.tosca_topology_template)

        self.used_conditions_set = conditions_set
        dict_tpl = copy.deepcopy(self.tosca_topology_template.tpl)
        if new_element_templates.get(NODES):
            dict_tpl[NODE_TEMPLATES] = new_element_templates[NODES]
        if new_element_templates.get(RELATIONSHIPS):
            dict_tpl[RELATIONSHIP_TEMPLATES] = new_element_templates[RELATIONSHIPS]

        rel_types = []
        for k, v in self.provider_defs.items():
            (_, element_type, _) = tosca_type.parse(k)
            if element_type == RELATIONSHIP_TYPES:
                rel_types.append(v)

        topology_tpl = TopologyTemplate(dict_tpl, self.full_provider_defs, rel_types)
        self.artifacts.extend(new_artifacts)
        self.extra_configuration_tool_params = deep_update_dict(self.extra_configuration_tool_params, new_extra)

        return topology_tpl
