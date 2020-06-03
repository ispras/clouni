import copy
from toscatranslator.common import tosca_type
from toscatranslator.common.tosca_reserved_keys import ATTRIBUTES, PROPERTIES, ARTIFACTS, NAME, CAPABILITIES, \
    REQUIREMENTS, INTERFACES, NODE, NODES, ROOT

from toscatranslator.providers.common.all_requirements import ProviderRequirements


class ProviderResource(object):

    def __init__(self, provider, node, relationship_templates):
        """

        :param node: class NodeTemplate from toscaparser
        :param relationship_templates: list of RelationshipTemplate from toscaparser
        """
        # NOTE: added as a parameter in toscatranslator.providers.common.tosca_template:ProviderToscaTemplate

        self.provider = provider
        self.nodetemplate = node
        self.name = node.name
        self.type = node.type
        (_, _, type_name) = tosca_type.parse(self.type)
        self.type_name = type_name
        # NOTE: filling the parameters from openstack definition to parse from input template
        node_type = node.type_definition  # toscaparser.elements.nodetype.NodeType
        self.definitions_by_name = None
        self.requirement_definitions = None
        self.set_definitions_by_name(node_type)
        self.attribute_keys = list(self.attribute_definitions_by_name().keys())
        self.property_keys = list(self.property_definitions_by_name().keys())
        self.requirement_keys = list(self.requirement_definitions_by_name().keys())
        self.artifact_keys = list(self.artifact_definitions_by_name().keys())
        self.capability_keys = list(self.capability_definitions_by_name().keys())
        self.relationship_templates = list()
        self.dependency_order = 0

        # NOTE: Get the parameters from template using provider definition
        self.configuration_args = dict()
        # NOTE: node is NodeTemplate instance
        for key in self.property_keys:
            value = node.get_property_value(key)
            if value is not None:
                self.configuration_args[key] = value

        for key in self.attribute_keys:
            value = node.entity_tpl.get(ATTRIBUTES, {}).get(key)
            if value is not None:
                self.configuration_args[key] = value

        capability_defs = self.capability_definitions_by_name()
        for cap_key, cap_def in capability_defs.items():
            properties = node.get_capabilities().get(cap_key)
            definition_property_keys = cap_def.get(PROPERTIES, {}).keys()
            if properties:
                for def_prop_key in definition_property_keys:
                    value = properties.get_property_value(def_prop_key)
                    if value:
                        self.configuration_args[def_prop_key] = value

        if hasattr(node, ARTIFACTS):
            # TODO: oneliner
            for key, value in node.artifacts:
                self.configuration_args[key] = value

        relationship_template_names = set()
        provider_requirements = ProviderRequirements(self.requirement_definitions, self.provider)
        self.requirements = provider_requirements.get_requirements(node)
        self.node_filter_artifacts = []
        for key, req in self.requirements.items():
            if type(req) is list:
                self.configuration_args[key] = list(v.get_value() for v in req)
                temp_req = req
            else:
                self.configuration_args[key] = req.get_value()
                temp_req = [req]
            for v in temp_req:
                relation = v.relationship
                if relation is not None:
                    _, _, type_name = tosca_type.parse(relation)
                    if type_name is None:
                        relationship_template_names.add(relation)

        for relation in relationship_templates:
            if relation.name in relationship_template_names:
                self.relationship_templates.append(relation)

        self.node_priority = self.compute_node_priorities(node.custom_def)

    def get_node_type_priority(self, node_type_definitions, node_type_name):
        """

        :param node_type_definitions:
        :param node_type_name:
        :return:
        """
        (_, _, type_short) = tosca_type.parse(node_type_name)
        if type_short == ROOT:
            return 0
        requirement_definitions = node_type_definitions.get(node_type_name, {}).get(REQUIREMENTS, [])
        max_dependency_priority = 0
        for i in requirement_definitions:
            for k, v in i.items():
                req_node_type = v.get(NODE)
                if not req_node_type == ROOT and not req_node_type == node_type_name:
                    p = self.get_node_type_priority(node_type_definitions, req_node_type)
                    if p > max_dependency_priority or max_dependency_priority == 0:
                        max_dependency_priority = p + 1
        if max_dependency_priority >= self.MAX_NUM_PRIORITIES:
            ProviderResource.MAX_NUM_PRIORITIES = max_dependency_priority + 1
        return max_dependency_priority

    def compute_node_priorities(self, node_type_definitions):
        """
        Use node type definitions to count priority of the node_type
        :param node_type_definitions: dict of node type definitions
        :return:
        """
        ProviderResource.MAX_NUM_PRIORITIES = 1
        node_priorities_by_type = {}
        for node_type_name, node_type_def in node_type_definitions.items():
            (_, element_type, type_short) = tosca_type.parse(node_type_name)
            if type_short != ROOT and element_type == NODES:
                node_priorities_by_type[node_type_name] = self.get_node_type_priority(node_type_definitions,
                                                                                      node_type_name)
        return node_priorities_by_type

    def set_definitions_by_name(self, node_type):
        """
        Get the definitions from ToscaTemplate of toscaparser
        Refactor the requirements as its definition is list, not dict
        :param node_type: class NodeTemplate of toscaparser
        :return: dict of key = name of category and value is a dict
        """
        requirement_defs_list = node_type.get_value(node_type.REQUIREMENTS, None, True) or []
        requirement_defs_dict = {}
        requirement_defs_list_with_name_added = []
        for req_def in requirement_defs_list:
            for req_name, req_params in req_def.items():
                cur_req_def = requirement_defs_dict.get(req_name)
                if cur_req_def:
                    if isinstance(cur_req_def, list):
                        requirement_defs_dict[req_name].append(req_params)
                    else:
                        requirement_defs_dict[req_name] = [cur_req_def, req_params]
                else:
                    requirement_defs_dict[req_name] = req_params
                copy_req_def = copy.copy(req_params)
                copy_req_def[NAME] = req_name
                requirement_defs_list_with_name_added.append(copy_req_def)

        # Fulfill the definitions
        self.definitions_by_name = dict(
            attributes=node_type.get_value(ATTRIBUTES) or {},
            properties=node_type.get_value(PROPERTIES) or {},
            capabilities=node_type.get_value(CAPABILITIES, None, True) or {},
            requirements=requirement_defs_dict,
            interfaces=node_type.get_value(INTERFACES) or {},
            artifacts=node_type.get_value(ARTIFACTS) or {}
        )
        self.requirement_definitions = requirement_defs_list_with_name_added

    def get_definitions_by_name(self, name):
        return self.definitions_by_name.get(name)

    def capability_definitions_by_name(self):
        return self.get_definitions_by_name(CAPABILITIES)

    def property_definitions_by_name(self):
        return self.get_definitions_by_name(PROPERTIES)

    def attribute_definitions_by_name(self):
        return self.get_definitions_by_name(ATTRIBUTES)

    def requirement_definitions_by_name(self):
        return self.get_definitions_by_name(REQUIREMENTS)

    def artifact_definitions_by_name(self):
        return self.get_definitions_by_name(ARTIFACTS)

    def node_priority_by_type(self):
        return self.node_priority.get(self.type)

