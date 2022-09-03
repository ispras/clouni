from toscaparser.imports import ImportsLoader
from toscaparser.topology_template import TopologyTemplate
from toscaparser.functions import GetProperty

from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import *

from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.providers.common.translator_to_provider import translate as translate_to_provider
from toscatranslator.providers.common.provider_resource import ProviderResource

from graphlib import TopologicalSorter

import os, copy, json, yaml, logging, sys, six

SEPARATOR = ':'

class ProviderToscaTemplate(object):
    REQUIRED_CONFIG_PARAMS = (TOSCA_ELEMENTS_MAP_FILE, TOSCA_ELEMENTS_DEFINITION_FILE)
    DEPENDENCY_FUNCTIONS = (GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT)
    DEFAULT_ARTIFACTS_DIRECTOR = ARTIFACTS

    def __init__(self, tosca_parser_template_object, provider, configuration_tool, cluster_name, host_ip_parameter, public_key_path,
                 is_delete, common_map_files=[]):
        self.provider = provider
        self.is_delete = is_delete
        self.host_ip_parameter = host_ip_parameter
        self.public_key_path = public_key_path
        self.configuration_tool = configuration_tool
        self.provider_config = ProviderConfiguration(self.provider)
        self.cluster_name = cluster_name
        for sec in self.REQUIRED_CONFIG_PARAMS:
            if not self.provider_config.config[self.provider_config.MAIN_SECTION].get(sec):
                logging.error("Provider configuration parameter \'%s\' has missing value" % sec)
                logging.error("Translating failed")
                sys.exit(1)

        map_files = self.provider_config.get_section(self.provider_config.MAIN_SECTION) \
            .get(TOSCA_ELEMENTS_MAP_FILE)
        if isinstance(map_files, six.string_types):
            map_files = [map_files]
        tosca_elements_map_files = []
        for file in map_files:
            map_file = file
            if not os.path.isabs(file):
                map_file = os.path.join(self.provider_config.config_directory, file)
            tosca_elements_map_files.append(map_file)

        self.map_files = common_map_files
        self.map_files.extend(tosca_elements_map_files)
        for file in self.map_files:
            if not os.path.isfile(file):
                logging.error("Mapping file for provider %s not found: %s" % (self.provider, file))
                sys.exit(1)

        topology_template = tosca_parser_template_object.topology_template
        self.inputs = topology_template.tpl.get(INPUTS, {})
        self.outputs = topology_template.tpl.get(OUTPUTS, {})
        self.definitions = topology_template.custom_defs

        self.node_templates = {}
        self.relationship_templates = {}
        self.template_mapping = {}
        for tmpl in topology_template.nodetemplates:
            self.node_templates[tmpl.name] = tmpl.entity_tpl

        for tmpl in topology_template.relationship_templates:
            self.relationship_templates[tmpl.name] = tmpl.entity_tpl
        import_definition_file = ImportsLoader([self.definition_file()], None, list(SERVICE_TEMPLATE_KEYS),
                                               topology_template.tpl)
        self.definitions.update(import_definition_file.get_custom_defs())
        self.software_types = set()
        self.fulfil_definitions_with_parents()
        self.artifacts = []
        self.used_conditions_set = set()
        self.extra_configuration_tool_params = dict()
        self.make_extended_notations()
        self.node_templates = self.resolve_get_property_functions(self.node_templates)
        self.relationship_templates = self.resolve_get_property_functions(self.relationship_templates)

        # resolving template dependencies fo normative templates
        self.template_dependencies = dict()
        self._relation_target_source = dict()
        self.resolve_in_template_dependencies()

        self.normative_nodes_graph = self.normative_nodes_graph_dependency()

        self.translate_to_provider()
        self.make_extended_notations()

        self.configuration_content = None
        self.configuration_ready = None

        self.template_dependencies = dict()
        self._relation_target_source = dict()
        self.resolve_in_template_dependencies()

        # After this step self.node_templates has requirements with node_filter parameter
        self.replace_requirements_with_node_filter()
        self.provider_nodes = self._provider_nodes()
        self.provider_relations = self._provider_relations()

        self.normative_nodes_graph = self.translate_normative_graph()

        # self.provider_node_names_by_priority = self._sort_nodes_by_priority()
        self.provider_operations, self.reversed_provider_operations = self.sort_nodes_and_operations_by_graph_dependency()

        # self.sub_graph_elements = []
        # for key, value in self.template_mapping.items():
        #    self.sub_graph_elements += [self.sort_nodes_and_operations_by_graph_dependency(value)]

    def _provider_nodes(self):
        """
        Create a list of ProviderResource classes to represent a node in TOSCA
        :return: list of class objects inherited from ProviderResource
        """
        provider_nodes = dict()
        for node_name, node in self.node_templates.items():
            (namespace, category, type_name) = utils.tosca_type_parse(node[TYPE])
            is_software_component = node[TYPE] in self.software_types
            if namespace != self.provider and not is_software_component or category != NODES:
                logging.error('Unexpected values: node \'%s\' not a software component and has a provider \'%s\'. '
                              'Node will be ignored' % (node.name, namespace))
            else:
                provider_node_instance = ProviderResource(self.provider, self.is_delete, self.cluster_name, self.configuration_tool, node,
                                                          node_name,
                                                          self.host_ip_parameter, self.definitions[node[TYPE]],
                                                          is_software_component=is_software_component)
                provider_nodes[node_name] = provider_node_instance
        return provider_nodes

    def _provider_relations(self):
        provider_relations = dict()
        for rel_name, rel_body in self.relationship_templates.items():
            provider_rel_instance = ProviderResource(self.provider, self.is_delete, self.cluster_name, self.configuration_tool, rel_body,
                                                     rel_name,
                                                     self.host_ip_parameter, self.definitions[rel_body[TYPE]],
                                                     is_relationship=True,
                                                     relation_target_source=self._relation_target_source)
            provider_relations[rel_name] = provider_rel_instance
        return provider_relations

    def _provider_nodes_by_name(self):
        """
        Get provider_nodes_by_name
        :return: self.provider_nodes_by_name
        """

        provider_nodes_by_name = dict()
        for node in self.provider_nodes:
            provider_nodes_by_name[node.nodetemplate.name] = node

        return provider_nodes_by_name

    def translate_normative_graph(self):
        """
            This method translates dependencies from nodes of normative template into
            dependencies between nodes in provider template
        """
        dependencies = {}
        for temp, dep in self.normative_nodes_graph.items():
            for elem in dep:
                for key, val in self.template_mapping.items():
                    if elem == key:
                        for tpl in self.template_mapping[temp]:
                            for el_tpl in self.template_mapping[elem]:
                                if tpl not in dependencies:
                                    dependencies[tpl] = {el_tpl}
                                else:
                                    dependencies[tpl].add(el_tpl)
        return dependencies

    def normative_nodes_graph_dependency(self):
        """
            This method generates dict of nodes, sorted by
            dependencies from normative TOSCA templates
        """
        nodes = set(self.node_templates.keys())
        dependencies = {}
        for templ_name in nodes:
            set_intersection = nodes.intersection(self.template_dependencies.get(templ_name, set()))
            utils.deep_update_dict(dependencies, {templ_name: set_intersection})
        return dependencies

    def update_relationships(self, new_dependencies, templ_name, direction, rel_name, post_op, banned_ops=[]):
        utils.deep_update_dict(new_dependencies, {
            templ_name + SEPARATOR + rel_name: {direction + SEPARATOR + post_op}})
        for key, value in new_dependencies.items():
            for elem in value:
                if elem == direction + SEPARATOR + post_op and key != templ_name + SEPARATOR + rel_name and key not in [
                    templ_name + SEPARATOR + x for x in banned_ops]:
                    utils.deep_update_dict(new_dependencies,
                                           {key: {templ_name + SEPARATOR + rel_name}})
        return new_dependencies

    def sort_nodes_and_operations_by_graph_dependency(self):
        """
            This method generates dict fith ProviderTemplates with operation, sorted by
            dependencies from normative and provider TOSCA templates
        """
        nodes = set(self.provider_nodes.keys())
        nodes = nodes.union(set(self.provider_relations.keys()))
        dependencies = {}
        lifecycle = ['configure', 'start', 'stop', 'delete']
        reversed_full_lifecycle = lifecycle[::-1] + ['create']
        # generate only dependencies from nodes
        for templ_name in nodes:
            set_intersection = nodes.intersection(self.template_dependencies.get(templ_name, set()))
            templ = self.provider_nodes.get(templ_name, self.provider_relations.get(templ_name))
            (_, element_type, _) = utils.tosca_type_parse(templ.type)
            if element_type == NODES:
                if 'interfaces' in templ.tmpl and 'Standard' in templ.tmpl['interfaces']:
                    new_operations = ['create']
                    # operation create always exists
                    for elem in lifecycle:
                        if elem in templ.tmpl['interfaces']['Standard']:
                            new_operations.append(elem)
                    # if there is any other operations - add ti new_operations and translate to dict
                    # in format {node.op: {node1, node2}}
                    # node requieres node1 and node2
                    if len(new_operations) == 1:
                        utils.deep_update_dict(dependencies, {templ_name + SEPARATOR + 'create': set_intersection})
                    else:
                        for i in range(1, len(new_operations)):
                            utils.deep_update_dict(dependencies, {
                                templ_name + SEPARATOR + new_operations[i]: {
                                    templ_name + SEPARATOR + new_operations[i - 1]}})
                        utils.deep_update_dict(dependencies,
                                               {templ_name + SEPARATOR + new_operations[0]: set_intersection})
                else:
                    utils.deep_update_dict(dependencies, {templ_name + SEPARATOR + 'create': set_intersection})
        new_normative_graph = {}

        # getting dependencies for create operaions of nodes, translated from 1 normative node
        for key, value in self.normative_nodes_graph.items():
            for elem in value:
                for op in reversed_full_lifecycle:
                    new_oper = elem + SEPARATOR + op
                    if new_oper in dependencies:
                        if key + SEPARATOR + 'create' in new_normative_graph:
                            new_normative_graph[key + SEPARATOR + 'create'].add(new_oper)
                        else:
                            new_normative_graph[key + SEPARATOR + 'create'] = {new_oper}
                        break
                else:
                    logging.error("Operation create not found")
                    sys.exit(1)
        # update dependencies
        dependencies = utils.deep_update_dict(dependencies, new_normative_graph)
        new_dependencies = {}
        # new_dependencies is needed for updating set operations
        # dict must be in format {node.op: {node1, node2}}
        for key, value in dependencies.items():
            new_set = set()
            for elem in value:
                for oper in reversed_full_lifecycle:
                    if elem + SEPARATOR + oper in dependencies:
                        new_set.add(elem + SEPARATOR + oper)
                        break
                    elif elem in dependencies:
                        new_set.add(elem)
                        break
            new_dependencies[key] = new_set

        # adding relationships operations pre_configure_source after create source node
        # pre_configure_target after create target node
        # add_source in parallel with pre_configure_source but in will be executed on target
        # post_configure_target after configure target node (if not configure then create - in parallel
        # with pre_configure_target)
        # post_configure_source after configure target node (if not configure then create - in parallel
        # with pre_configure_source)
        # other - not supported!
        for templ_name in nodes:
            templ = self.provider_nodes.get(templ_name, self.provider_relations.get(templ_name))
            (_, element_type, _) = utils.tosca_type_parse(templ.type)
            if element_type == RELATIONSHIPS:
                if 'interfaces' in templ.tmpl and 'Configure' in templ.tmpl['interfaces']:
                    if 'pre_configure_source' in templ.tmpl['interfaces']['Configure']:
                        new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.source,
                                                                     'pre_configure_source', 'create', ['add_source'])
                    if 'pre_configure_target' in templ.tmpl['interfaces']['Configure']:
                        new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.target,
                                                                     'pre_configure_target', 'create')
                    if 'post_configure_source' in templ.tmpl['interfaces']['Configure']:
                        if templ.source + SEPARATOR + 'configure' in new_dependencies:
                            new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.source,
                                                                         'post_configure_source', 'configure')
                        else:
                            new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.source,
                                                                         'post_configure_source', 'create')
                    if 'post_configure_target' in templ.tmpl['interfaces']['Configure']:
                        if templ.target + SEPARATOR + 'configure' in new_dependencies:
                            new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.target,
                                                                         'post_configure_target', 'configure')
                        else:
                            new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.target,
                                                                         'post_configure_target', 'create')
                    if 'add_source' in templ.tmpl['interfaces']['Configure']:
                        new_dependencies = self.update_relationships(new_dependencies, templ.name, templ.source,
                                                                     'add_source', 'create', ['pre_configure_source'])
                    if 'add_target' in templ.tmpl['interfaces']['Configure']:
                        logging.warning('Operation add_target not supported, it will be skipped')
                    if 'target_changed' in templ.tmpl['interfaces']['Configure']:
                        logging.warning('Operation target_changed not supported, it will be skipped')
                    if 'remove_target' in templ.tmpl['interfaces']['Configure']:
                        logging.warning('Operation remove_target not supported, it will be skipped')
        # mapping strings 'node.op' to provider template of this node with this operation
        templ_mappling = {}
        for elem in new_dependencies:
            templ_name = elem.split(SEPARATOR)[0]
            templ = copy.deepcopy(self.provider_nodes.get(templ_name, self.provider_relations.get(templ_name)))
            templ.operation = elem.split(SEPARATOR)[1]
            templ_mappling[elem] = templ
        templ_dependencies = {}
        reversed_templ_dependencies = {}
        # create dict where all elements will be replaced with provider template from templ_mappling
        # reversed_templ_dependencies needed for delete - it just a reversed version of graph
        for key, value in new_dependencies.items():
            new_set = set()
            for elem in value:
                new_set.add(templ_mappling[elem])
                if templ_mappling[elem] not in reversed_templ_dependencies:
                    reversed_templ_dependencies[templ_mappling[elem]] = {templ_mappling[key]}
                elif templ_mappling[key] not in reversed_templ_dependencies[templ_mappling[elem]]:
                    reversed_templ_dependencies[templ_mappling[elem]].add(templ_mappling[key])
            templ_dependencies[templ_mappling[key]] = new_set
        if len(templ_dependencies) <= 1:
            reversed_templ_dependencies = copy.copy(templ_dependencies)
        return templ_dependencies, reversed_templ_dependencies

    def add_template_dependency(self, node_name, dependency_name):
        if not dependency_name == SELF and not node_name == dependency_name:
            if self.template_dependencies.get(node_name) is None:
                self.template_dependencies[node_name] = {dependency_name}
            else:
                self.template_dependencies[node_name].add(dependency_name)

    def replace_requirements_with_node_filter(self):
        for node_name, node in self.node_templates.items():
            for req in node.get(REQUIREMENTS, []):
                for req_name, req_body in req.items():
                    if req_body.get(NODE):
                        node_tmpl = self.node_templates.get(req_body[NODE])
                        node_filter = dict()
                        properties = node_tmpl.get(PROPERTIES)
                        props_list = []
                        if properties:
                            for prop_name, prop in properties.items():
                                props_list.append({prop_name: prop})
                        capabilities = node_tmpl.get(CAPABILITIES)
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
                        req_body[NODE_FILTER] = node_filter
                        req[req_name] = req_body

    def resolve_in_template_dependencies(self):
        """
        TODO think through the logic to replace mentions by id
        Changes all mentions of node_templates by name in requirements, places dictionary with node_filter instead
        :return:
        """
        for node_name, node in self.node_templates.items():
            for req in node.get(REQUIREMENTS, []):
                for req_name, req_body in req.items():

                    # Valid keys are ('node', 'node_filter', 'relationship', 'capability', 'occurrences')
                    # Only node and relationship might be a template name or a type
                    req_relationship = req_body.get(RELATIONSHIP)
                    req_node = req_body.get(NODE)

                    if req_relationship is not None:
                        (_, _, type_name) = utils.tosca_type_parse(req_relationship)
                        if type_name is None:
                            self.add_template_dependency(node_name, req_relationship)
                            self._relation_target_source[req_relationship] = {
                                'source': node_name,
                                'target': req_node
                            }

                    if req_node is not None:
                        (_, _, type_name) = utils.tosca_type_parse(req_node)
                        if type_name is None:
                            self.add_template_dependency(node_name, req_node)

            node_types_from_requirements = set()
            req_definitions = self.definitions[node[TYPE]].get(REQUIREMENTS, [])
            for req in req_definitions:
                for req_name, req_def in req.items():
                    if req_def.get(NODE, None) is not None:
                        if req_def[NODE] != node[TYPE]:
                            node_types_from_requirements.add(req_def[NODE])
            for req_node_name, req_node_tmpl in self.node_templates.items():
                if req_node_tmpl[TYPE] in node_types_from_requirements:
                    self.add_template_dependency(node_name, req_node_name)

        # Search in all nodes for get function mentions and get its target name

        for node_name, node_tmpl in self.node_templates.items():
            self.search_get_function(node_name, node_tmpl)

        for rel_name, rel_tmpl in self.relationship_templates.items():
            self.search_get_function(rel_name, rel_tmpl)

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
                        if self.relationship_templates.get(template_name) is not None and \
                                self._relation_target_source.get(template_name) is None:
                            self._relation_target_source[template_name] = {
                                'source': node_name,
                                'target': None
                            }
        elif isinstance(data, list):
            for i in data:
                self.search_get_function(node_name, i)
        elif isinstance(data, (str, int, float)):
            return

    def definition_file(self):
        file_definition = self.provider_config.config['main'][TOSCA_ELEMENTS_DEFINITION_FILE]
        if not os.path.isabs(file_definition):
            file_definition = os.path.join(self.provider_config.config_directory, file_definition)

        if not os.path.isfile(file_definition):
            logging.error("TOSCA definition file not found: %s" % file_definition)
            sys.exit(1)

        return file_definition

    def tosca_elements_map_to_provider(self):
        r = dict()
        for file in self.map_files:
            with open(file, 'r') as file_obj:
                data = file_obj.read()
                try:
                    data_dict = json.loads(data)
                    r.update(data_dict)
                except:
                    try:
                        data_dict = yaml.safe_load(data)
                        r.update(data_dict)
                    except yaml.scanner.ScannerError as e:
                        logging.error("Mapping file \'%s\' must be of type JSON or YAMl" % file)
                        logging.error("Error parsing TOSCA template: %s%s" % (e.problem, e.context_mark))
                        sys.exit(1)
        return r

    def translate_to_provider(self):
        new_element_templates, new_extra, template_mapping = translate_to_provider(self)

        dict_tpl = {}
        self.template_mapping = template_mapping
        if new_element_templates.get(NODES):
            dict_tpl[NODE_TEMPLATES] = new_element_templates[NODES]
        if new_element_templates.get(RELATIONSHIPS):
            dict_tpl[RELATIONSHIP_TEMPLATES] = new_element_templates[RELATIONSHIPS]
        if new_element_templates.get(OUTPUTS):
            dict_tpl[OUTPUTS] = new_element_templates[OUTPUTS]
        if self.inputs:
            dict_tpl[INPUTS] = self.inputs

        rel_types = {}
        for k, v in self.definitions.items():
            (_, element_type, _) = utils.tosca_type_parse(k)
            if element_type == RELATIONSHIPS:
                rel_types[k] = v

        logging.debug("TOSCA template with non normative types for provider %s was generated: \n%s"
                      % (self.provider, yaml.dump(dict_tpl)))

        try:
            topology_tpl = TopologyTemplate(dict_tpl, self.definitions, rel_types=rel_types)
        except:
            logging.exception("Failed to parse intermidiate non-normative TOSCA template with OpenStack tosca-parser")
            sys.exit(1)

        self.extra_configuration_tool_params = utils.deep_update_dict(self.extra_configuration_tool_params, new_extra)

        self.node_templates = new_element_templates.get(NODES, {})
        self.relationship_templates = new_element_templates.get(RELATIONSHIPS, {})
        self.outputs = new_element_templates.get(OUTPUTS, {})

    def _get_property_value(self, value, tmpl_name):
        prop_keys = []
        tmpl_properties = None

        if value[0] == SELF:
            value[0] = tmpl_name
        if value[0] == HOST:
            value = [tmpl_name, 'host'] + value[1:]
        if value[0] in [SOURCE, TARGET]:
            # TODO
            logging.critical("Not implemented")
            sys.exit(1)
        node_tmpl = self.node_templates[value[0]]

        if node_tmpl.get(REQUIREMENTS, None) is not None:
            for req in node_tmpl[REQUIREMENTS]:
                if req.get(value[1], None) is not None:
                    if req[value[1]].get(NODE, None) is not None:
                        return self._get_property_value([req[value[1]][NODE]] + value[2:], req[value[1]][NODE])
                    if req[value[1]].get(NODE_FILTER, None) is not None:
                        tmpl_properties = {}
                        node_filter_props = req[value[1]][NODE_FILTER].get(PROPERTIES, [])
                        for prop in node_filter_props:
                            tmpl_properties.update(prop)
                        prop_keys = value[2:]
        if node_tmpl.get(CAPABILITIES, {}).get(value[1], None) is not None:
            tmpl_properties = node_tmpl[CAPABILITIES][value[1]].get(PROPERTIES, {})
            prop_keys = value[2:]
        if node_tmpl.get(PROPERTIES, {}).get(value[1], None) is not None:
            tmpl_properties = node_tmpl[PROPERTIES]
            prop_keys = value[1:]

        for key in prop_keys:
            if tmpl_properties.get(key, None) is None:
                tmpl_properties = None
                break
            tmpl_properties = tmpl_properties[key]
        if tmpl_properties is None:
            logging.error("Failed to get property: %s" % json.dumps(value))
            sys.exit(1)
        return tmpl_properties

    def resolve_get_property_functions(self, data=None, tmpl_name=None):
        if data is None:
            data = self.node_templates
        if isinstance(data, dict):
            new_data = {}
            for key, value in data.items():
                if key == GET_PROPERTY:
                    new_data = self._get_property_value(value, tmpl_name)
                else:
                    new_data[key] = self.resolve_get_property_functions(value,
                                                                        tmpl_name if tmpl_name is not None else key)
            return new_data
        elif isinstance(data, list):
            new_data = []
            for v in data:
                new_data.append(self.resolve_get_property_functions(v, tmpl_name))
            return new_data
        elif isinstance(data, GetProperty):
            value = data.args
            return self._get_property_value(value, tmpl_name)
        return data

    def make_extended_notations(self):
        for tpl_name, tpl in self.node_templates.items():
            if tpl.get(REQUIREMENTS, None) is not None:
                for req in tpl[REQUIREMENTS]:
                    for req_name, req_body in req.items():
                        if isinstance(req_body, six.string_types):
                            req[req_name] = {
                                'node': req_body
                            }
            if tpl.get(ARTIFACTS, None) is not None:
                for art_name, art_body in tpl[ARTIFACTS].items():
                    if isinstance(art_body, six.string_types):
                        tpl[ARTIFACTS][art_name] = {
                            'file': art_body
                        }
            if tpl.get(INTERFACES, None) is not None:
                for inf_name, inf_body in tpl[INTERFACES].items():
                    for op_name, op_body in inf_body.items():
                        if op_name not in [DERIVED_FROM, TYPE, DESCRIPTION, INPUTS]:
                            if isinstance(op_body, six.string_types):
                                tpl[INTERFACES][inf_name][op_name] = {
                                    IMPLEMENTATION: {
                                        'primary': op_body,
                                        'dependencies': []
                                    },
                                    INPUTS: []
                                }
                            elif isinstance(op_body, list):
                                tpl[INTERFACES][inf_name][op_name] = {
                                    IMPLEMENTATION: {
                                        'primary': op_body[0] if len(op_body) >= 1 else [],
                                        'dependencies': op_body[1:] if len(op_body) >= 2 else []
                                    },
                                    INPUTS: []
                                }

    def __repr__(self):
        s = "tosca_definitions_version: tosca_simple_yaml_1_0\n\n" + "topology_template:\n" + "  node_templates:\n"
        if len(self.node_templates) == 0:
            return s

        for (k, v) in self.node_templates[0].templates.items():
            s += "    - " + k + ":\n        "
            one = yaml.dump(v)
            one = one.replace('\n', '\n        ')
            s += one + "\n"
        return s

    def _get_full_defintion(self, definition, def_type, ready_set):
        if def_type in ready_set:
            return definition, def_type in self.software_types

        (_, _, def_type_short) = utils.tosca_type_parse(def_type)
        is_software_type = def_type_short == 'SoftwareComponent'
        is_software_parent = False
        parent_def_name = definition.get(DERIVED_FROM, None)
        if parent_def_name is not None:
            if def_type == parent_def_name:
                logging.critical("Invalid type \'%s\' is derived from itself" % def_type)
                sys.exit(1)
            if parent_def_name in ready_set:
                parent_definition = self.definitions[parent_def_name]
                is_software_parent = parent_def_name in self.software_types
            else:
                parent_definition, is_software_parent = \
                    self._get_full_defintion(self.definitions[parent_def_name], parent_def_name, ready_set)
            parent_definition = copy.deepcopy(parent_definition)
            definition = utils.deep_update_dict(parent_definition, definition)
        if is_software_type or is_software_parent:
            self.software_types.add(def_type)
        ready_set.add(def_type)
        return definition, def_type in self.software_types

    def fulfil_definitions_with_parents(self):
        ready_definitions = set()
        for def_name, definition in self.definitions.items():
            self.definitions[def_name], _ = self._get_full_defintion(definition, def_name, ready_definitions)
