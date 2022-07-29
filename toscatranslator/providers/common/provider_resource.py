import os
import sys

import six

from toscatranslator.common import utils
from toscatranslator.configuration_tools.ansible.runner import prepare_for_run

from toscatranslator.providers.common.all_requirements import ProviderRequirements

import copy, logging
from toscatranslator.common.tosca_reserved_keys import *
from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.providers.common.translator_to_provider import execute

SET_FACT_SOURCE = "set_fact"
IMPORT_TASKS_MODULE = "include"

class ProviderResource(object):

    def __init__(self, provider, is_delete, cluster_name, configuration_tool, tmpl, node_name, host_ip_parameter, node_type, is_software_component=False, is_relationship=False,
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
        self.cluster_name = cluster_name
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
        self.operation = None
        self.is_delete = is_delete

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
                        if host_ip_parameter not in ('public_address', 'private_address'):
                            host_ip_parameter = 'private_address'
                        self.host = req.data['node'] + '_' + host_ip_parameter

            self.node_filter_artifacts = []
            for key, req in self.requirements.items():
                if type(req) is list:
                    self.configuration_args[key] = list(v.get_value() for v in req)
                else:
                    self.configuration_args[key] = req.get_value()

            if configuration_tool == 'ansible':
                provider_config = ProviderConfiguration(provider)
                node_filter_config = provider_config.get_subsection(ANSIBLE, NODE_FILTER)
                if not node_filter_config:
                    node_filter_config = {}
                node_filter_source_prefix = node_filter_config.get('node_filter_source_prefix', '')
                node_filter_source_postfix = node_filter_config.get('node_filter_source_postfix', '')
                node_filter_exceptions = node_filter_config.get('node_filter_exceptions', '')
                node_filter_inner_variable = node_filter_config.get('node_filter_inner_variable')
                node_filter_inner_value = node_filter_config.get('node_filter_inner_value')
                if node_filter_inner_value:
                    if not isinstance(node_filter_inner_value, dict):
                        logging.error("Provider configuration parameter "
                                      "\'ansible.node_filter: node_filter_inner_value\' is missing "
                                      "or has unsupported value \'%s\'" % node_filter_inner_value)
                        sys.exit(1)
                    else:
                        for elem in node_filter_inner_value:
                            if elem in self.configuration_args:
                                if self.configuration_args[elem].get(VALUE):
                                    self.configuration_args[elem][VALUE] = node_filter_inner_value[elem]
                for arg_key, arg in self.configuration_args.items():
                    if isinstance(arg, dict):
                        node_filter_key = arg.get(SOURCE, {}).get(NODE_FILTER)
                        node_filter_value = arg.get(VALUE)
                        node_filter_params = arg.get(PARAMETERS)

                        if node_filter_key and node_filter_value and node_filter_params:
                            node_filter_source = node_filter_source_prefix + node_filter_key + node_filter_source_postfix
                            if node_filter_exceptions:
                                if node_filter_exceptions.get(node_filter_key):
                                    node_filter_source = node_filter_exceptions[node_filter_key]

                            NODE_FILTER_FACTS = 'node_filter_facts'
                            NODE_FILTER_FACTS_REGISTER = NODE_FILTER_FACTS + '_raw'
                            NODE_FILTER_FACTS_VALUE = NODE_FILTER_FACTS_REGISTER
                            if node_filter_inner_variable:
                                if isinstance(node_filter_inner_variable, dict):
                                    node_filter_inner_variable = node_filter_inner_variable.get(node_filter_key, '')
                                if isinstance(node_filter_inner_variable, six.string_types):
                                    node_filter_inner_variable = [node_filter_inner_variable]
                                if isinstance(node_filter_inner_variable, list):
                                    for v in node_filter_inner_variable:
                                        NODE_FILTER_FACTS_VALUE += '[\"' + v + '\"]'
                                else:
                                    logging.error("Provider configuration parameter "
                                                  "\'ansible.node_filter: node_filter_inner_variable\' is missing "
                                                  "or has unsupported value \'%s\'" % node_filter_inner_variable)
                                    sys.exit(1)

                            tmp_ansible_tasks = [
                                {
                                    SOURCE: node_filter_source,
                                    VALUE: NODE_FILTER_FACTS_REGISTER,
                                    EXECUTOR: configuration_tool,
                                    PARAMETERS: {}
                                },
                                {
                                    SOURCE: SET_FACT_SOURCE,
                                    PARAMETERS: {
                                        "target_objects": "\\{\\{ " + NODE_FILTER_FACTS_VALUE + " \\}\\}"
                                    },
                                    VALUE: "tmp_value",
                                    EXECUTOR: configuration_tool
                                },
                                {
                                    SOURCE: 'debug',
                                    PARAMETERS: {
                                        'var': 'target_objects'
                                    },
                                    VALUE: "tmp_value",
                                    EXECUTOR: configuration_tool
                                },
                                {
                                    SOURCE: SET_FACT_SOURCE,
                                    PARAMETERS: {
                                        "input_facts": '{{ target_objects }}'
                                    },
                                    EXECUTOR: configuration_tool,
                                    VALUE: "tmp_value"
                                },
                                {
                                    SOURCE: SET_FACT_SOURCE,
                                    PARAMETERS: {
                                        "input_args": node_filter_params
                                    },
                                    EXECUTOR: configuration_tool,
                                    VALUE: "tmp_value"
                                },
                                {
                                    SOURCE: IMPORT_TASKS_MODULE,
                                    PARAMETERS: "artifacts/equals.yaml",
                                    EXECUTOR: configuration_tool,
                                    VALUE: "tmp_value"
                                },
                                {
                                    SOURCE: SET_FACT_SOURCE,
                                    PARAMETERS: {
                                        node_filter_value: "\{\{ matched_object[\"" + node_filter_value + "\"] \}\}"
                                    },
                                    VALUE: "tmp_value",
                                    EXECUTOR: configuration_tool
                                }
                            ]
                            arg = str(execute(tmp_ansible_tasks, self.is_delete, self.cluster_name, node_filter_value))
                    self.configuration_args[arg_key] = arg

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
