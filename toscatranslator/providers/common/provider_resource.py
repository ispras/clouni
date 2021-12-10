import sys

from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import PROPERTIES, ARTIFACTS, NAME, CAPABILITIES, \
    REQUIREMENTS, TYPE, RELATIONSHIP, DEFAULT

from toscatranslator.providers.common.all_requirements import ProviderRequirements

import copy, logging


class ProviderResource(object):

    def __init__(self, provider, tmpl, node_name, node_type, is_software_component=False, is_relationship=False,
                 relation_target_source = dict()):
        """

        :param provider:
        :param tmpl:
        :param node_name:
        :param node_type:
        :param is_software_component:
        :param is_relationship:
        """

        self.provider = provider
        self.tmpl = tmpl
        self.name = node_name
        self.type = tmpl[TYPE]
        (_, _, type_name) = utils.tosca_type_parse(self.type)
        self.type_name = type_name
        self.type_definition = node_type
        self.is_software_component = is_software_component
        self.host = None
        self.self = node_name
        self.target = None
        self.source = None
        self.dependency_order = 0

        self.set_defaults()
        # NOTE: Get the parameters from template using provider definition
        self.configuration_args = dict()
        # NOTE: node is NodeTemplate instance
        for key in self.type_definition.get(PROPERTIES, {}).keys():
            value = self.tmpl.get(PROPERTIES, {}).get(key, None)
            if value is not None:
                self.configuration_args[key] = value

        # NOTE: filling the parameters from openstack definition to parse from input template
        if is_relationship:
            self.source = relation_target_source.get(self.name, {}).get('source')
            self.target = relation_target_source.get(self.name, {}).get('target')
        else:
            capability_defs = self.type_definition.get(CAPABILITIES, {})
            for cap_key, cap_def in capability_defs.items():
                properties = self.tmpl.get(CAPABILITIES, {}).get(cap_key)
                definition_property_keys = cap_def.get(PROPERTIES, {}).keys()
                if properties:
                    for def_prop_key in definition_property_keys:
                        value = properties.get_property_value(def_prop_key)
                        if value:
                            self.configuration_args[def_prop_key] = value

            for key, value in self.tmpl.get(ARTIFACTS, []):
                self.configuration_args[key] = value

            provider_requirements = ProviderRequirements(self.requirement_definitions, self.provider)
            self.requirements = provider_requirements.get_requirements(tmpl)

            for req_name, reqs in self.requirements.items():
                if isinstance(reqs, list):
                    iter_reqs =  reqs
                else:
                    iter_reqs = [reqs]
                for req in iter_reqs:
                    relationship = req.definition[RELATIONSHIP]
                    (_, _, type_name) = utils.tosca_type_parse(relationship)
                    if type_name == 'HostedOn':
                        if self.host is not None:
                            logging.critical("Node \'\' can be hosted only on one node" % self.name)
                            sys.exit(1)
                        self.host = req.value

            self.node_filter_artifacts = []
            for key, req in self.requirements.items():
                if type(req) is list:
                    self.configuration_args[key] = list(v.get_value() for v in req)
                else:
                    self.configuration_args[key] = req.get_value()

    @property
    def requirement_definitions(self):
        """
        Refactor the requirements as its definition is list, not dict
        :return: dict of key = name of category and value is a dict
        """
        requirement_defs_list = self.type_definition.get(REQUIREMENTS, None) or []
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

        return requirement_defs_list_with_name_added
    def set_defaults(self):
        for prop_name, prop_def in self.type_definition.get(PROPERTIES, {}).items():
            value = self.tmpl.get(PROPERTIES, {}).get(prop_name)
            default = prop_def.get(DEFAULT)
            if default is not None and value is None:
                self.tmpl[PROPERTIES] = self.tmpl.get(PROPERTIES, {})
                self.tmpl[PROPERTIES][prop_name] = default
