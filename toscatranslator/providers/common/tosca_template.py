from toscaparser.imports import ImportsLoader
from toscaparser.topology_template import TopologyTemplate
from toscaparser.functions import GetProperty
from toscaparser.functions import GetAttribute
from toscaparser.functions import GetInput

from toscatranslator.common.tosca_reserved_keys import *
from toscatranslator.common import utils

from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider
from toscatranslator.providers.common.provider_resource import ProviderResource

import os, copy, json, yaml, logging, sys

SEPARATOR = '.'


class ProviderToscaTemplate(object):
    REQUIRED_CONFIG_PARAMS = (TOSCA_ELEMENTS_MAP_FILE, TOSCA_ELEMENTS_DEFINITION_FILE) = \
        ('tosca_elements_map_file', 'tosca_elements_definition_file')
    DEPENDENCY_FUNCTIONS = (GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT)
    DEFAULT_ARTIFACTS_DIRECTOR = ARTIFACTS

    def __init__(self, tosca_parser_template, provider, cluster_name):
        self.provider = provider
        self.provider_config = ProviderConfiguration(self.provider)
        self.cluster_name = cluster_name
        for sec in self.REQUIRED_CONFIG_PARAMS:
            if not self.provider_config.config[self.provider_config.MAIN_SECTION].get(sec):
                logging.error("Provider configuration parameter \'%s\' has missing value" % sec )
                logging.error("Translating failed")
                sys.exit(1)

        # toscaparser.tosca_template:ToscaTemplate
        self.tosca_parser_template = tosca_parser_template
        # toscaparser.topology_template:TopologyTemplate
        self.tosca_topology_template = self.full_type_definitions(self.tosca_parser_template.topology_template)

        import_definition_file = ImportsLoader([self.definition_file()], None, list(SERVICE_TEMPLATE_KEYS),
                                               self.tosca_topology_template.tpl)
        self.full_provider_defs = copy.copy(self.tosca_topology_template.custom_defs)
        self.provider_defs = import_definition_file.get_custom_defs()
        self.full_provider_defs.update(self.provider_defs)

        self.artifacts = []
        self.used_conditions_set = set()
        self.extra_configuration_tool_params = dict()
        self.inputs = self.tosca_topology_template.inputs
        self.outputs = self.tosca_topology_template.outputs
        # TODO use get property functions
        node_templates = self.resolve_get_property_functions(self.tosca_topology_template.nodetemplates)
        node_templates = self.resolve_get_attribute_functions(self.tosca_topology_template.nodetemplates)
        node_templates = self.resolve_get_input_functions(self.tosca_topology_template.nodetemplates)

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
        self.software_component_names = []
        for node in self.node_templates:
            if self._is_software_component(node):
                self.software_component_names.append(node.name)
        logging.debug("Software components are used: %s" % json.dumps(self.software_component_names))
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
            (namespace, category, type_name) = utils.tosca_type_parse(node.type)
            is_software_component = node.name in self.software_component_names
            if namespace != self.provider and not is_software_component or category != NODES:
                logging.error('Unexpected values: node \'%s\' not a software component and has a provider \'%s\'. '
                              'Node will be ignored' % (node.name, namespace))
            else:
                provider_node_instance = ProviderResource(self.provider, node, self.relationship_templates,
                                                          is_software_component)
                provider_nodes.append(provider_node_instance)

        return provider_nodes

    def full_type_definitions(self, topology_template):
        for node in topology_template.nodetemplates:
            node.type_definition = utils.get_full_type_definition(node.type_definition)
        return topology_template

    def _sort_nodes_by_priority(self):
        """
        Every ProviderResource child class has priority which reflects in order of objects to create in configuration dsl

        :return: dictionary with keys = priority
        """
        sorted_by_priority = dict()
        max_priority = 0
        for node in self.provider_nodes:
            if not node.name in self.software_component_names:
                priority = node.node_priority_by_type()
                priority_sorted = sorted_by_priority.get(priority, [])
                priority_sorted.append(node.nodetemplate.name)
                sorted_by_priority[priority] = priority_sorted
                if priority > max_priority:
                    max_priority = priority
        max_priority += 1
        for i in range(max_priority):
            if sorted_by_priority.get(i, None) is None:
                sorted_by_priority[i] = []
        sorted_by_priority[max_priority] = self.software_component_names
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

    def _is_software_component(self, node):
        tmp = copy.copy(node)
        while tmp != None:
            if tmp.type == 'tosca.nodes.SoftwareComponent':
                return True
            tmp = tmp.parent_type
        return False

    def sort_nodes_by_dependency(self):
        """
        Use dependency requirement between nodes of the same type, check dependency of different types
        :param self.template_dependencies
        :param self.relationship_templates_by_name
        :param self.provider_node_names_by_priority
        :param self.provider_nodes_by_name
        :return: List of nodes sorted by priority
        """

        group_by_templ_name = dict()
        group = 0
        template_names = []
        deps_extended_with_priority = copy.copy(self.template_dependencies)
        for priority in range(len(self.provider_node_names_by_priority)):
            if priority == 0:
                continue
            for node_name in self.provider_node_names_by_priority[priority]:
                for i in range(priority):
                    deps_extended_with_priority[node_name] = \
                        deps_extended_with_priority.get(node_name, set()).union(set(self.provider_node_names_by_priority[i]))

        nodes_left_next = set(self.provider_nodes_by_name.keys())
        nodes_left_next = nodes_left_next.union(set(self.relationship_templates_by_name.keys()))
        infinite_error = False
        while len(nodes_left_next) > 0 and not infinite_error:
            nodes_left = copy.copy(nodes_left_next)
            infinite_error = True
            for templ_name in nodes_left:
                set_intersection = nodes_left_next.intersection(deps_extended_with_priority.get(templ_name, set()))
                if len(set_intersection) == 0:
                    infinite_error = False
                    template_names.append(templ_name)
                    nodes_left_next.remove(templ_name)
                    group_by_templ_name[templ_name] = group
            group += 1
        # Here we added nodes of the same priority
        if infinite_error:
            logging.error('Resolving dependencies for nodes by priority failed for nodes: %s'
                          % json.dumps(nodes_left_next))
            sys.exit(1)

        templates = []
        for templ_name in template_names:
            templ = self.provider_nodes_by_name.get(templ_name, self.relationship_templates_by_name.get(templ_name))
            if templ is None:
                logging.critical("Failed to resolve dependencies in intermediate non-normative TOSCA template. "
                                 "Template \'%s\' is missing." % templ_name)
                sys.exit(1)
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
                            _, _, type_name = utils.tosca_type_parse(req_relationship)
                            if type_name is None:
                                self.add_template_dependency(node.name, req_relationship)

                        if req_node is not None:
                            _, _, type_name = utils.tosca_type_parse(req_node)
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
            logging.error("TOSCA definition file not found: %s" % file_definition)
            sys.exit(1)

        return file_definition

    def tosca_elements_map_to_provider(self):
        tosca_elements_map_file = self.provider_config.config['main'][self.TOSCA_ELEMENTS_MAP_FILE]
        if not os.path.isabs(tosca_elements_map_file):
            tosca_elements_map_file = os.path.join(self.provider_config.config_directory, tosca_elements_map_file)

        if not os.path.isfile(tosca_elements_map_file):
            logging.error("Mapping file for provider %s not found: %s" % (self.provider, tosca_elements_map_file))
            sys.exit(1)

        with open(tosca_elements_map_file, 'r') as file_obj:
            data = file_obj.read()
            try:
                data_dict = json.loads(data)
            except:
                try:
                    data_dict = yaml.safe_load(data)
                except yaml.scanner.ScannerError as e:
                    logging.error("Mapping file \'%s\' must be of type JSON or YAMl" % tosca_elements_map_file)
                    logging.error("Error parsing TOSCA template: %s%s" % (e.problem, e.context_mark))
                    sys.exit(1)
        return data_dict

    def translate_to_provider(self):
        new_element_templates, new_artifacts, conditions_set, new_extra = translate_to_provider(
            self.tosca_elements_map_to_provider(), self.tosca_topology_template, self.provider)

        self.used_conditions_set = conditions_set
        dict_tpl = copy.deepcopy(self.tosca_topology_template.tpl)
        if new_element_templates.get(NODES):
            dict_tpl[NODE_TEMPLATES] = new_element_templates[NODES]
        if new_element_templates.get(RELATIONSHIPS):
            dict_tpl[RELATIONSHIP_TEMPLATES] = new_element_templates[RELATIONSHIPS]

        rel_types = {}
        for k, v in self.full_provider_defs.items():
            (_, element_type, _) = utils.tosca_type_parse(k)
            if element_type == RELATIONSHIPS:
                rel_types[k] = v

        logging.debug("TOSCA template with non normative types for provider %s was generated: \n%s"
                      % (self.provider, yaml.dump(dict_tpl)))

        try:
            topology_tpl = TopologyTemplate(dict_tpl, self.full_provider_defs, rel_types=rel_types)
        except:
            logging.exception("Failed to parse intermidiate non-normative TOSCA template with OpenStack tosca-parser")
            sys.exit(1)
        self.artifacts.extend(new_artifacts)
        self.extra_configuration_tool_params = utils.deep_update_dict(self.extra_configuration_tool_params, new_extra)

        return topology_tpl

    def _get_all_get_properties(self, data, path=''):
        r = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k == GET_PROPERTY:
                    r.append({path: v})
                r.extend(self._get_all_get_properties(v, SEPARATOR.join([path, k])))
        elif isinstance(data, list):
            for i in range(len(data)):
                r.extend(self._get_all_get_properties(data[i], SEPARATOR.join([path, str(i)])))
        elif isinstance(data, GetProperty):
            r.append({path: data.args})
        return r

    def resolve_get_property_functions(self, nodes):
        functions = []
        nodes_by_name = {}
        for node in nodes:
            functions.extend(self._get_all_get_properties(node.entity_tpl, node.name))
            nodes_by_name[node.name] = node
        for function in functions:
            for f_name, f_body in function.items():
                dep_node = nodes_by_name[f_body[0]]
                function[f_name] = dep_node.entity_tpl[PROPERTIES][f_body[1]]
            for i in range(2, len(f_body)):
                function[f_name] = function[f_name][f_body[i]]
        for function in functions:
            for f_name, f_body in function.items():
                f_name_splitted = f_name.split(SEPARATOR)
                tpl = nodes_by_name[f_name_splitted[0]].entity_tpl
                for i in range(1, len(f_name_splitted)-1):
                    tpl = tpl[f_name_splitted[i]]
                tpl[f_name_splitted[-1]] = f_body
        return nodes

    def _get_all_get_attributes(self, data, path=''):
        r = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k == GET_ATTRIBUTE:
                    r.append({path: v})
                r.extend(self._get_all_get_attributes(v, SEPARATOR.join([path, k])))
        elif isinstance(data, list):
            for i in range(len(data)):
                r.extend(self._get_all_get_attributes(data[i], SEPARATOR.join([path, str(i)])))
        elif isinstance(data, GetAttribute):
            r.append({path: data.args})
        return r

    def resolve_get_attribute_functions(self, nodes):
        functions = []
        nodes_by_name = {}
        for node in nodes:
            functions.extend(self._get_all_get_attributes(node.entity_tpl, node.name))
            nodes_by_name[node.name] = node
        for function in functions:
            for f_name, f_body in function.items():
                dep_node = nodes_by_name[f_body[0]]
                function[f_name] = dep_node.entity_tpl[ATTRIBUTES][f_body[1]]
            for i in range(2, len(f_body)):
                function[f_name] = function[f_name][f_body[i]]
        for function in functions:
            for f_name, f_body in function.items():
                f_name_splitted = f_name.split(SEPARATOR)
                tpl = nodes_by_name[f_name_splitted[0]].entity_tpl
                for i in range(1, len(f_name_splitted)-1):
                    tpl = tpl[f_name_splitted[i]]
                tpl[f_name_splitted[-1]] = f_body
        return nodes

    def _get_all_get_inputs(self, data, path=''):
        pass

    def resolve_get_input_functions(self, nodes):
        pass