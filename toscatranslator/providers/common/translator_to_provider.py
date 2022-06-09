import ast
from multiprocessing import Queue

import yaml

from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import *
from toscatranslator.configuration_tools.combined.combine_configuration_tools import get_configuration_tool_class

from random import randint, seed
from time import time

import copy, six, logging, sys, json, re

SEPARATOR = '.'
MAP_KEY = "map"
SET_FACT_SOURCE = "set_fact"
INDIVISIBLE_KEYS = [GET_OPERATION_OUTPUT, INPUTS, IMPLEMENTATION, GET_ATTRIBUTE]
BUFFER = 'buffer'

ARTIFACT_RANGE_START = 1000
ARTIFACT_RANGE_END = 9999
PYTHON_EXECUTOR = 'python'
PYTHON_SOURCE_DIRECTORY = 'toscatranslator.providers.common.python_sources'
TMP_DIRECTORY = '/tmp/clouni'


def translate_element_from_provider(tmpl_name, node_tmpl):
    (_, element_type, _) = utils.tosca_type_parse(node_tmpl[TYPE])
    node_templates = {
        element_type: {
            tmpl_name: copy.deepcopy(node_tmpl)
        }
    }
    return node_templates


def get_structure_of_mapped_param(mapped_param, value, input_value=None, indivisible=False, if_list_type=False):
    if mapped_param is None:
        # NOTE The case when parameter was 'input_value'
        return [], None
    if input_value is None:
        input_value = value

    if isinstance(mapped_param, str):
        splitted_mapped_param = mapped_param.split(SEPARATOR)
        if splitted_mapped_param[-1] in INDIVISIBLE_KEYS:
            indivisible = True
        if not indivisible:
            if isinstance(value, list):
                r = []
                len_v = len(value)
                if len_v == 1:
                    param, _ = get_structure_of_mapped_param(mapped_param, value[0], input_value, if_list_type=True)
                    return param, None

                for v in value:
                    if isinstance(v, str):
                        # Error! Stucks in recursion if {get_property: []} is used
                        param, _ = get_structure_of_mapped_param(SEPARATOR.join([mapped_param, v]), input_value,
                                                                 input_value)
                    else:
                        param, _ = get_structure_of_mapped_param(mapped_param, v, input_value)
                    r += param
                return r, None

            if isinstance(value, dict):
                r = dict()
                for k, v in value.items():
                    # Error! Stucks in recursion if {get_property: []} is used
                    param, _ = get_structure_of_mapped_param(k, v, input_value)
                    for p in param:
                        r = utils.deep_update_dict(r, p)
                r, _ = get_structure_of_mapped_param(mapped_param, r, input_value, indivisible=True,
                                                     if_list_type=if_list_type)
                return r, None

        # NOTE: end of recursion
        structure = value
        if if_list_type:
            structure = [value]
        for i in range(len(splitted_mapped_param), 0, -1):
            structure = {
                splitted_mapped_param[i - 1]: structure
            }
        return [structure], None

    if isinstance(mapped_param, list):
        r = []
        for p in mapped_param:
            param, _ = get_structure_of_mapped_param(p, value, input_value)
            r += param
        return r, None

    if isinstance(mapped_param, dict):
        # NOTE: Assert number of keys! Always start of recursion?
        num_of_keys = len(mapped_param.keys())
        if num_of_keys == 1 or num_of_keys == 2 and KEYNAME in mapped_param.keys():
            for k, v in mapped_param.items():
                if k != PARAMETER and k != KEYNAME:
                    param, _ = get_structure_of_mapped_param(k, v, input_value)
                    if isinstance(param, tuple):
                        (param, keyname) = param
                        if mapped_param.get(KEYNAME):
                            mapped_param[KEYNAME] = keyname
                    return param, mapped_param.get(KEYNAME)
        else:
            # TODO find the cases
            assert False

    logging.critical("Unable to parse the following parameter: %s" % json.dumps(mapped_param))
    sys.exit(1)


def restructure_value(mapping_value, self, if_format_str=True, if_upper=True):
    """
    Recursive function which processes the mapping_value to become parameter:value format
    :param mapping_value: the map of non normative parameter:value
    :param self: the function used to store normative parameter, value and other values
    :param if_format_str:
    :param if_upper: detects if the parameter value must be saved
    :return: dict in the end of recursion, because the first is always (parameter, value) keys
    """
    if isinstance(mapping_value, dict):
        flat_mapping_value = dict()
        for key in MAPPING_VALUE_KEYS:
            mapping_sub_value = mapping_value.get(key)
            if mapping_sub_value is not None:
                restructured_value = restructure_value(mapping_sub_value, self, if_format_str=key != PARAMETER,
                                                       if_upper=False)
                if restructured_value is None:
                    logging.critical("Unable to parse the following parameter: %s" % json.dumps(mapping_value))
                    sys.exit(1)
                flat_mapping_value[key] = restructured_value

        # NOTE: the case when value has keys ERROR and REASON
        if flat_mapping_value.get(ERROR, False):
            logging.error('Unable to use unsupported TOSCA parameter: %s'
                          % flat_mapping_value.get(REASON).format(self=self))
            sys.exit(1)

        # NOTE: the case when value has keys PARAMETER, VALUE, KEYNAME
        parameter = flat_mapping_value.get(PARAMETER)
        value = flat_mapping_value.get(VALUE)
        keyname = flat_mapping_value.get(KEYNAME)
        if value is None:
            # The case when variable is indivisible
            # This case parameter and keyname are None too or they doesn't have sense
            filled_value = dict()
            for k, v in mapping_value.items():
                filled_k = restructure_value(k, self, if_upper=False)
                filled_v = restructure_value(v, self, if_upper=False)
                filled_value[filled_k] = filled_v
            return filled_value
        if parameter is not None:
            if not isinstance(parameter, six.string_types):
                logging.critical("Unable to parse the following parameter: %s" % json.dumps(parameter))
                sys.exit(1)
            if parameter[:6] == '{self[' and parameter[-1] == '}':
                logging.critical("Parameter is format value, but has to be resolved on this stage: %s"
                                 % json.dumps(parameter))
                sys.exit(1)
            r = dict()
            r[parameter] = value

            if if_upper:
                # r[PARAMETER] = parameter
                if keyname:
                    r[KEYNAME] = keyname
            return r

        # NOTE: the case when value has keys SOURCE, PARAMETERS, EXTRA, VALUE, EXECUTOR
        source_name = flat_mapping_value.get(SOURCE)
        parameters_dict = flat_mapping_value.get(PARAMETERS)
        extra_parameters = flat_mapping_value.get(EXTRA)
        executor_name = flat_mapping_value.get(EXECUTOR)
        if source_name is not None and executor_name is not None:
            if executor_name == PYTHON_EXECUTOR:
                return utils.execute_function(PYTHON_SOURCE_DIRECTORY, source_name, parameters_dict)
            else:
                tool = get_configuration_tool_class(executor_name)()
                extension = tool.get_artifact_extension()

                seed(time())
                artifact_name = '_'.join([self[NAME], executor_name, source_name,
                                          str(randint(ARTIFACT_RANGE_START, ARTIFACT_RANGE_END))]) + extension

                flat_mapping_value.update(
                    name=artifact_name,
                    configuration_tool=executor_name
                )

            if not get_configuration_tool_class(executor_name):
                logging.critical('Unsupported executor/configuration tool name: %s' % executor_name)
                sys.exit(1)
            if self.get(ARTIFACTS) is None:
                self[ARTIFACTS] = []

            self[ARTIFACTS].append(flat_mapping_value)
            # return the name of artifact
            return artifact_name

        logging.error("Unable to parse the following parameter: %s" % json.dumps(mapping_value))
        sys.exit(1)

    elif isinstance(mapping_value, list):
        return [restructure_value(v, self, if_upper=False) for v in mapping_value]

    if isinstance(mapping_value, str) and if_format_str:
        # NOTE: the process is needed because using only format function makes string from json
        mapping_value, _ = format_value(mapping_value, self, False)
    return mapping_value


def replace_brackets(data, with_splash=True):
    if isinstance(data, six.string_types):
        if with_splash:
            return data.replace("{", "\{").replace("}", "\}")
        else:
            return data.replace("\\\\{", "{").replace("\\{", "{").replace("\{", "{") \
                .replace("\\\\}", "}").replace("\\}", "}").replace("\}", "}")
    if isinstance(data, dict):
        r = {}
        for k, v in data.items():
            r[replace_brackets(k)] = replace_brackets(v, with_splash)
        return r
    if isinstance(data, list):
        r = []
        for i in data:
            r.append(replace_brackets(i, with_splash))
        return r
    return data


def format_value(value, params, if_replace_brackets=True):
    is_buffer = False
    params_without_buffer = copy.deepcopy(params)
    params_without_buffer.pop(BUFFER)
    if isinstance(value, six.string_types):
        value_format = value.replace("\\\\{", "{{").replace("\\{", "{{") \
            .replace("\\\\}", "}}").replace("\\}", "}}")
        try:
            temp_val = value_format.format(self=params_without_buffer)
            is_buffer = False
        except KeyError:
            try:
                temp_val = value_format.format(self=params)
                is_buffer = True
            except KeyError:
                return value, is_buffer
        try:
            if temp_val == value_format:
                temp_val = value.replace("\\\\{", "{").replace("\\{", "{") \
                    .replace("\\\\}", "}").replace("\\}", "}")
            dict_val = temp_val.replace("\'", "\"")
            dict_val = json.loads(dict_val)
            if if_replace_brackets:
                dict_val = replace_brackets(dict_val)
            return dict_val, is_buffer
        except json.decoder.JSONDecodeError:
            if if_replace_brackets:
                temp_val = replace_brackets(temp_val)
            return temp_val, is_buffer
    if isinstance(value, list):
        r = []
        for v in value:
            f, temp_is_buffer = format_value(v, params, if_replace_brackets)
            is_buffer = is_buffer or temp_is_buffer
            r.append(f)
        return r, is_buffer
    if isinstance(value, dict):
        r = dict()
        for k, v in value.items():
            format_key, temp_is_buffer = format_value(k, params, if_replace_brackets)
            is_buffer = temp_is_buffer or is_buffer
            r[format_key], temp_is_buffer = format_value(v, params, if_replace_brackets)
            is_buffer = temp_is_buffer or is_buffer
        return r, is_buffer
    return value, is_buffer


def get_resulted_mapping_values(parameter, mapping_value, value, self):
    """
    Manage the case when mapping value has multiple structures in mapping_value
    :param parameter:
    :param mapping_value:
    :param value:
    :return:
    """
    mapping_value = copy.deepcopy(mapping_value)
    if isinstance(mapping_value, six.string_types):
        mapping_value = {
            PARAMETER: mapping_value,
            VALUE: "{self[value]}"
        }
    mapping_value_parameter = mapping_value.get(PARAMETER)
    mapping_value_value = mapping_value.get(VALUE)
    # NOTE at first check if parameter self[buffer] parameter
    if mapping_value_parameter and mapping_value_parameter[:6] == '{self[' and mapping_value_parameter[-2:] == ']}':
        self[VALUE] = value
        self[PARAMETER] = parameter
        # The case when variable is written to the parameter self!
        # Inside string can be more self parameters
        if isinstance(mapping_value_value, dict):
            if mapping_value_value.get(VALUE) and mapping_value_value.get(EXECUTOR) == PYTHON_EXECUTOR and \
                    mapping_value_value.get(SOURCE):
                args, _ = format_value(mapping_value_value[PARAMETERS], self)
                mapping_value_value = utils.execute_function(PYTHON_SOURCE_DIRECTORY, mapping_value_value[SOURCE],
                                                             args)
        params_parameter = mapping_value_parameter[6:-2].split('][')
        iter_value, is_buffer = format_value(mapping_value_value, self)
        if is_buffer:
            return dict(
                parameter=parameter,
                map=dict(
                    parameter=mapping_value_parameter,
                    value=mapping_value_value
                ),
                value=value
            )
        iter_num = len(params_parameter)
        for i in range(iter_num - 1, 0, -1):
            temp_param = dict()
            param_key, _ = format_value(params_parameter[i], self)
            temp_param[param_key] = iter_value
            iter_value = temp_param
        utils.deep_update_dict(self, {params_parameter[0]: iter_value})
        return []
    elif mapping_value_parameter:
        splitted_mapping_value_parameter = mapping_value_parameter.split(SEPARATOR)
        has_section = False
        for v in splitted_mapping_value_parameter:
            if v in NODE_TEMPLATE_KEYS:
                has_section = True
                break
        if not has_section:
            if isinstance(mapping_value_value, list) and len(mapping_value_value) > 1:
                r = []
                for v in mapping_value_value:
                    mapping_value[VALUE] = v
                    item = get_resulted_mapping_values(parameter, mapping_value, value, self)
                    if isinstance(item, list):
                        if len(item) == 1:
                            item = [item]
                    else:
                        item = [item]
                    r.extend(item)
                return r
            if isinstance(mapping_value_value, six.string_types):
                splitted_mapping_value_value = mapping_value_value.split(SEPARATOR)
                for i in range(len(splitted_mapping_value_value)):
                    if splitted_mapping_value_value[i] in NODE_TEMPLATE_KEYS:
                        mapping_value[PARAMETER] = mapping_value_parameter + SEPARATOR + mapping_value_value
                        mapping_value[VALUE] = "{self[value]}"
                        return dict(
                            parameter=parameter,
                            map=mapping_value,
                            value=value
                        )

            if isinstance(mapping_value_value, dict):
                # NOTE the only valid case when the value is parameter-value structure
                mapping_value_value_parameter = mapping_value_value.get(PARAMETER)
                mapping_value_value_value = mapping_value_value.get(VALUE)
                if mapping_value_value_parameter and mapping_value_value_value:
                    mapping_value_value_keyname = mapping_value_value.get(KEYNAME)
                    if mapping_value_value_keyname:
                        mapping_value[KEYNAME] = mapping_value_value_keyname
                    mapping_value[PARAMETER] = mapping_value_parameter + SEPARATOR + mapping_value_value_parameter
                    mapping_value[VALUE] = mapping_value_value_value
                    r = get_resulted_mapping_values(parameter, mapping_value, value, self)
                    return r

            logging.critical("Unable to parse the following parameter: %s" % json.dumps(mapping_value))
            sys.exit(1)

    return dict(
        parameter=parameter,
        map=mapping_value,
        value=value
    )


def is_matched_mapping_value(mapping_value):
    """
    Check if input param is actual mapping value: it is not if it's a dict and doesn't have structure of mapping_value
    :param mapping_value: dict
    :return: boolean
    """
    if isinstance(mapping_value, dict):
        for supported_structure in SUPPORTED_MAPPING_VALUE_STRUCTURE:
            matched = True
            for k in supported_structure:
                if mapping_value.get(k) is None:
                    matched = False
                    break
            if matched:
                return True
        return False
    if isinstance(mapping_value, list):
        for v in mapping_value:
            if not is_matched_mapping_value(v):
                return False
    return True


def get_restructured_mapping_item(key_prefix, parameter, mapping_value, value, self):
    """
    Is used for recursion
    :param key_prefix:
    :param parameter:
    :param mapping_value:
    :param value:
    :return: list of dict
    """
    if mapping_value is None:
        return None

    if isinstance(mapping_value, list):
        r = []
        for v in mapping_value:
            item = get_restructured_mapping_item(key_prefix, parameter, v, value, self)
            if isinstance(item, list):
                r.extend(item)
            elif item is not None:
                r.append(item)
        return r

    if is_matched_mapping_value(mapping_value):
        # NOTE: end of recursion, when parameter is found
        # ERROR floating_ip example, the value is the list but not
        resulted_mapping_values = get_resulted_mapping_values(parameter, mapping_value, value, self)
        return resulted_mapping_values

    if isinstance(value, dict):
        r = []
        for _k, v in value.items():
            for k in [_k, '*']:
                arg_key_prefix = k if not key_prefix else SEPARATOR.join([key_prefix, k])
                arg_map = mapping_value.get(arg_key_prefix)
                if arg_map is None:
                    arg_map = mapping_value
                else:
                    arg_key_prefix = ''
                arg_parameter = k if not parameter else SEPARATOR.join([parameter, k])
                item = get_restructured_mapping_item(arg_key_prefix, arg_parameter, arg_map, v, self)
                if isinstance(item, list):
                    r.extend(item)
                elif item is not None:
                    r.append(item)
        return r

    if isinstance(value, list):
        r = []
        for v in value:
            item = get_restructured_mapping_item(key_prefix, parameter, mapping_value, v, self)
            if isinstance(item, list):
                r.extend(item)
            elif item is not None:
                r.append(item)
        return r

    if isinstance(value, str):
        r = []
        arg_key_prefix = value if not key_prefix else SEPARATOR.join([key_prefix, value])
        arg_map = mapping_value.get(arg_key_prefix)
        if not arg_map:
            arg_map = mapping_value
        else:
            arg_key_prefix = ''
        arg_parameter = value if not parameter else SEPARATOR.join([parameter, value])
        item = get_restructured_mapping_item(arg_key_prefix, arg_parameter, arg_map, True, self)
        if isinstance(item, list):
            r.extend(item)
        elif item is not None:
            r.append(item)
        return r

    return None


def split_parameter(parameter):
    splitted_parameter = parameter.split(SEPARATOR)
    for i in range(len(splitted_parameter)):
        if splitted_parameter[i] in NODE_TEMPLATE_KEYS:
            node_type = SEPARATOR.join(splitted_parameter[:i])
            return node_type, splitted_parameter[i:]
    return parameter, []


def get_node_type_from_parameter(parameter):
    node_type, _ = split_parameter(parameter)
    return node_type


def restructure_mapping(service_tmpl, node_tmpl, tmpl_name, self):
    """
    Restructure the mapping elements to make the mapping uniform the only 1 version to be interpreted.
    Only assigned with value parameters are mentioned
    Restructured output is list of objects with keys: ('parameter', 'value', 'map'), parameter is a normative parameter,
        value is a value of normative parameter, map is a resulting specialized parameter:value map
    :param tosca_elements_map_to_provider: input mapping from file.yaml
    :param node: input node to be mapped
    :return: restructured_mapping: dict
    """
    tosca_elements_map_to_provider = service_tmpl.tosca_elements_map_to_provider()
    template = {}
    for section in NODE_TEMPLATE_KEYS:
        section_value = node_tmpl.get(section)
        if section_value is not None:
            template[section] = section_value

    self[NAME] = tmpl_name
    r = []
    node_type = node_tmpl[TYPE]
    prev_node_type = None
    while node_type != None and prev_node_type != node_type:
        r_parent = get_restructured_mapping_item('', '', tosca_elements_map_to_provider, {node_type: template}, self)
        r_parent.extend(r)
        r = r_parent
        prev_node_type = node_type
        node_type = service_tmpl.definitions[node_type].get(DERIVED_FROM)
    if prev_node_type == node_type:
        logging.critical("Type \'%s\' is derived from itself" % node_type)
        sys.exit(1)
    for i in range(len(r)):
        # NOTE: the case when value has keys ERROR and REASON
        if r[i][MAP_KEY].get(ERROR, False):
            logging.error("Unable to use unsupported TOSCA parameter \'%s\': %s" %
                          (r[i][PARAMETER], r[i][MAP_KEY].get(REASON).format(self=self)))
            sys.exit(1)
        parameter_node_type = get_node_type_from_parameter(r[i][PARAMETER])
        mapping_node_type = get_node_type_from_parameter(r[i][MAP_KEY][PARAMETER])
        if parameter_node_type == mapping_node_type and parameter_node_type != node_tmpl[TYPE]:
            r[i][PARAMETER] = r[i][PARAMETER].replace(parameter_node_type, node_tmpl[TYPE])
            r[i][MAP_KEY][PARAMETER] = r[i][MAP_KEY][PARAMETER].replace(mapping_node_type, node_tmpl[TYPE])
    return r


def resolve_self_in_buffer(data, self):
    if isinstance(data, six.string_types):
        data, _ = format_value(data, self)
        if not isinstance(data, six.string_types):
            return resolve_self_in_buffer(data, self)
        else:
            return data
    if isinstance(data, dict):
        r = {}
        for k, v in data.items():
            r[k] = resolve_self_in_buffer(v, self)
        return r
    if isinstance(data, list):
        r = []
        for i in data:
            r.append(resolve_self_in_buffer(i, self))
        return r
    return data


def restructure_mapping_buffer(restructured_mapping, self):
    self[BUFFER] = resolve_self_in_buffer(self[BUFFER], self)
    r = []
    for mapping in restructured_mapping:
        parameter = mapping[MAP_KEY][PARAMETER]
        filter = "\{self\[buffer\]"
        if re.search(filter, parameter):
            self[VALUE] = mapping[VALUE]
            self[PARAMETER] = mapping[PARAMETER]
            iter_value, _ = format_value(mapping[MAP_KEY][VALUE], self)
            params_parameter = parameter[6:-2].split('][')
            iter_num = len(params_parameter)
            for i in range(iter_num - 1, 0, -1):
                temp_param = dict()
                temp_param[params_parameter[i]] = iter_value
                iter_value = temp_param
            utils.deep_update_dict(self, {params_parameter[0]: iter_value})
        else:
            r.append(mapping)
    return r


def retrieve_node_templates(input_dict, input_prefix=None):
    r = dict()
    for k, v in input_dict.items():
        if k in NODE_TEMPLATE_KEYS:
            return {input_prefix: input_dict}
        t = retrieve_node_templates(v, SEPARATOR.join([input_prefix, k]) if input_prefix else k)
        r = utils.deep_update_dict(r, t)
    return r


def get_keyname_from_type(keyname, node_type):
    (_, _, type_name) = utils.tosca_type_parse(node_type)
    if not type_name:
        logging.critical("Unable to parse type name: %s" % json.dumps(node_type))
        sys.exit(1)
    return keyname + "_" + utils.snake_case(type_name)


def translate_node_from_tosca(restructured_mapping, tpl_name, self):
    """
    Translator from TOSCA definitions in provider definitions using rules from element_map_to_provider
    :param restructured_mapping: list of dicts(parameter, map, value)
    :param tpl_name: str
    :return: entity_tpl as dict
    """
    resulted_structure = {}

    for item in restructured_mapping:
        self[PARAMETER] = item[PARAMETER]
        self[VALUE] = item[VALUE]
        mapped_param = restructure_value(
            mapping_value=item[MAP_KEY],
            self=self
        )
        structures, keyname = get_structure_of_mapped_param(mapped_param, item[VALUE])

        for structure in structures:
            r = retrieve_node_templates(structure)
            for node_type, tpl in r.items():
                if not keyname:
                    keyname = get_keyname_from_type(self[KEYNAME], node_type)
                node_tpl_with_name = {keyname: {node_type: tpl}}
                resulted_structure = utils.deep_update_dict(resulted_structure, node_tpl_with_name)

    for keyname, node in resulted_structure.items():
        for node_type, tpl in node.items():
            if tpl.get(REQUIREMENTS):
                reqs = []
                for req_name, req in tpl[REQUIREMENTS].items():
                    reqs.append({
                        req_name: req
                    })
                resulted_structure[keyname][node_type][REQUIREMENTS] = reqs
    return resulted_structure


def get_source_structure_from_facts(self, condition, fact_name, value, arguments, executor, target_parameter,
                                    source_parameter,
                                    source_value):
    """
    :param condition:
    :param fact_name:
    :param value:
    :param arguments:
    :param executor
    :param target_parameter:
    :param source_parameter:
    :param source_value:
    :return:
    """

    if isinstance(fact_name, six.string_types):
        if isinstance(arguments, list):
            for i in range(len(arguments)):
                if isinstance(arguments[i], str) and 'self' in arguments[i]:
                    for key in re.findall(r'([a-z]+)', arguments[i]):
                        if key != 'self':
                            self = self[key]
                    arguments[i] = self
        fact_name_splitted = fact_name.split(SEPARATOR)
        source_name = fact_name_splitted[0]
        facts_result = "facts_result"
        if len(fact_name_splitted) > 1:
            facts_result += "[\"" + "\"][\"".join(fact_name_splitted[1:]) + "\"]"
        facts_result = "\\{\\{ " + facts_result + " \\}\\}"
        new_global_elements_map_total_implementation = [
            {
                SOURCE: source_name,
                VALUE: "facts_result",
                EXECUTOR: executor,
                PARAMETERS: {}
            },
            {
                SOURCE: SET_FACT_SOURCE,
                PARAMETERS: {
                    "target_objects": facts_result
                },
                VALUE: "tmp_value",
                EXECUTOR: executor
            },
            {
                SOURCE: 'debug',
                PARAMETERS: {
                    'var': 'target_objects'
                },
                VALUE: "tmp_value",
                EXECUTOR: executor
            },
            {
                SOURCE: SET_FACT_SOURCE,
                PARAMETERS: {
                    "input_facts": '{{ target_objects }}'
                },
                EXECUTOR: executor,
                VALUE: "tmp_value"
            },
            {
                SOURCE: SET_FACT_SOURCE,
                PARAMETERS: {
                    "input_args": arguments
                },
                EXECUTOR: executor,
                VALUE: "tmp_value"
            },
            {
                SOURCE: "include",
                PARAMETERS: "artifacts/" + condition + ".yaml",
                EXECUTOR: executor,
                VALUE: "tmp_value"
            },
            {
                SOURCE: SET_FACT_SOURCE,
                PARAMETERS: {
                    value: "\{\{ matched_object[\"" + value + "\"] \}\}"
                },
                VALUE: "tmp_value",
                EXECUTOR: executor
            }
        ]
    else:
        new_global_elements_map_total_implementation = fact_name

    if executor == 'ansible':
        configuration_class = get_configuration_tool_class(executor)()
        new_ansible_artifacts = copy.deepcopy(new_global_elements_map_total_implementation)
        for i in range(len(new_ansible_artifacts)):
            extension = configuration_class.get_artifact_extension()

            seed(time())
            new_ansible_artifacts[i]['name'] = '_'.join(
                [SOURCE, str(randint(ARTIFACT_RANGE_START, ARTIFACT_RANGE_END))]) + extension
            new_ansible_artifacts[i]['configuration_tool'] = executor
        artifacts_with_brackets = replace_brackets(new_ansible_artifacts, False)
        new_ansible_tasks, _ = utils.generate_artifacts(configuration_class, artifacts_with_brackets, TMP_DIRECTORY,
                                                        store=False)

        q = Queue()
        playbook = {
            'hosts': 'localhost',
            'tasks': new_ansible_tasks
        }
        configuration_class.prepare_for_run(TMP_DIRECTORY)
        configuration_class.parallel_run([playbook], 'artifacts', q)

        # есть такая проблема что если в текущем процессе был запущен runner cotea то все последующие запуски
        # других плейбуков из этого процесса невозможны т.к. запускаться будет первоначальный плейбук, причем даже если
        # этот процесс форкнуть то эффект остается тк что то там внутри cotea сохраняется в контексте процесса
        results = q.get()
        value = None
        if_failed = False
        for result in results:
            if result.is_failed or result.is_unreachable:
                logging.error("Task %s has failed because of exception: \n%s" %
                              (result.task_name, result.result.get('exception', '(Unknown reason)')))
                if_failed = True
            if 'results' in result.result and len(result.result['results']) > 0 and 'ansible_facts' in \
                    result.result['results'][0] and 'matched_object' in result.result['results'][0]['ansible_facts']:
                value = result.result['results'][0]['ansible_facts']['matched_object'][target_parameter.split('.')[-1]]
        if if_failed:
            sys.exit(1)

        return value


def restructure_mapping_facts(elements_map, self, extra_elements_map=None, target_parameter=None, source_parameter=None,
                              source_value=None):
    """
    Function is used to restructure mapping values with the case of `facts`, `condition`, `arguments`, `value` keys
    :param elements_map:
    :param self:
    :param extra_elements_map:
    :param target_parameter:
    :param source_parameter:
    :param source_value:
    :return:
    """
    conditions = []
    elements_map = copy.deepcopy(elements_map)
    if not extra_elements_map:
        extra_elements_map = []

    if isinstance(elements_map, dict):
        cur_parameter = elements_map.get(PARAMETER)
        if cur_parameter and isinstance(cur_parameter, str):
            if elements_map.get(MAP_KEY):
                source_parameter = cur_parameter
                source_value = elements_map.get(VALUE)
            elif target_parameter:
                target_parameter += SEPARATOR + cur_parameter
            else:
                target_parameter = cur_parameter
        new_elements_map = dict()
        for k, v in elements_map.items():
            cur_elements, extra_elements_map, new_conditions = restructure_mapping_facts(v, self, extra_elements_map,
                                                                                         target_parameter,
                                                                                         source_parameter, source_value)
            new_elements_map.update({k: cur_elements})
            conditions.extend(new_conditions)

        if isinstance(new_elements_map.get(PARAMETER, ''), dict):
            separated_target_parameter = target_parameter.split(SEPARATOR)
            target_type = None
            target_short_parameter = None
            for i in range(len(separated_target_parameter)):
                if separated_target_parameter[i] in NODE_TEMPLATE_KEYS:
                    target_type = SEPARATOR.join(separated_target_parameter[:i])
                    target_short_parameter = '_'.join(separated_target_parameter[i:])
                    break
            if not target_short_parameter or not target_type:
                logging.critical("Unable to parse the following parameter: %s" % json.dumps(target_parameter))
                sys.exit(1)

            input_parameter = new_elements_map[PARAMETER]
            input_value = new_elements_map[VALUE]
            input_keyname = new_elements_map.get(KEYNAME)

            provider = separated_target_parameter[0]
            target_relationship_type = SEPARATOR.join([provider, RELATIONSHIPS, "DependsOn"])
            relationship_name = "{self[name]}_server_" + utils.snake_case(separated_target_parameter[-1])

            operation_name = 'modify_' + target_short_parameter
            value_name = 'modified_' + target_short_parameter
            interface_name = 'Extra'
            new_elements_map = {
                GET_OPERATION_OUTPUT: [relationship_name, interface_name, operation_name, value_name]
            }

            cur_target_parameter = SEPARATOR.join(
                [target_relationship_type, INTERFACES, interface_name, operation_name])
            cur_extra_element = {
                PARAMETER: source_parameter,
                MAP_KEY: {
                    PARAMETER: cur_target_parameter,
                    KEYNAME: relationship_name,
                    VALUE: {
                        IMPLEMENTATION: {
                            SOURCE: SET_FACT_SOURCE,
                            VALUE: "default_value",
                            EXECUTOR: ANSIBLE,
                            PARAMETERS: {
                                value_name: "\\{\\{ input_parameter: input_value \\}\\}"
                            }
                        },
                        INPUTS: {
                            "input_parameter": input_parameter,
                            "input_value": input_value
                        }
                    }
                },
                VALUE: source_value
            }
            if input_keyname:
                # TODO add keyname to the parameter outside the new_elements_map
                cur_extra_element[map][KEYNAME] = input_keyname
            extra_elements_map.append(cur_extra_element)

        if_facts_structure = False
        keys = new_elements_map.keys()
        if len(keys) > 0:
            if_facts_structure = True
            for k in FACTS_MAPPING_VALUE_STRUCTURE:
                if k not in keys:
                    if_facts_structure = False
        if if_facts_structure:
            # NOTE: end of recursion
            assert target_parameter

            condition = new_elements_map[CONDITION]
            fact_name = new_elements_map[FACTS]
            value = new_elements_map[VALUE]
            arguments = new_elements_map[ARGUMENTS]
            executor = new_elements_map[EXECUTOR]
            if not get_configuration_tool_class(executor):
                logging.critical("Unsupported executor name \'%s\'" % json.dumps(executor))
                sys.exit(1)
            new_elements_map = get_source_structure_from_facts(self, condition, fact_name, value, arguments, executor,
                                            target_parameter, source_parameter,
                                            source_value)
            conditions.append(condition)

        return new_elements_map, extra_elements_map, conditions

    if isinstance(elements_map, list):
        new_elements_map = []
        for k in elements_map:
            cur_elements, extra_elements_map, new_conditions = restructure_mapping_facts(k, self, extra_elements_map,
                                                                                         target_parameter,
                                                                                         source_parameter, source_value)
            new_elements_map.append(cur_elements)
            conditions.extend(new_conditions)
        return new_elements_map, extra_elements_map, conditions

    return elements_map, extra_elements_map, conditions


def restructure_get_attribute(data, service_tmpl, self):
    r = data
    if isinstance(data, list):
        r = []
        for i in data:
            r.append(restructure_get_attribute(i, service_tmpl, self))
    elif isinstance(data, dict):
        r = {}
        for k, v in data.items():
            if k == GET_ATTRIBUTE:
                args = restructure_get_attribute(v, service_tmpl, self)
                node_type = service_tmpl.node_templates[args[0]]['type']
                parameter = SEPARATOR.join([node_type, ATTRIBUTES] + args[1:])
                self = copy.copy(self)
                self[PARAMETER] = parameter
                value = True
                for i in range(len(args) - 1, 0, -1):
                    value = {args[i]: value}
                value = {node_type: {ATTRIBUTES: value}}
                self[VALUE] = value
                self[NAME] = args[0]
                self[KEYNAME] = args[0]
                items = get_restructured_mapping_item('', '', service_tmpl.tosca_elements_map_to_provider(), value,
                                                      self)
                attribute_items = []
                for item in items:
                    if re.search(parameter, item[PARAMETER]):
                        attribute_items.append(item)
                if len(attribute_items) == 0:
                    logging.error("Can not parse \'get_attribute\', mapping not found: %s" % json.dumps(args))
                    sys.exit(1)
                if len(attribute_items) > 1:
                    logging.critical("Not implemented, must have an example to work through logic")
                    sys.exit(1)
                mapping_parameter = attribute_items[0][MAP_KEY][PARAMETER]
                map_node_type, splitted_param = split_parameter(mapping_parameter)
                if splitted_param[0] != ATTRIBUTES:
                    logging.error("Attributes can only be mapped to the attributes, error occured with %s"
                                  % json.dumps(data))
                    sys.exit(1)
                r[k] = [get_keyname_from_type(self[KEYNAME], map_node_type)] + splitted_param[1:]
            else:
                r[k] = restructure_get_attribute(v, service_tmpl, self)
    return r


def translate(service_tmpl):
    """
    Main function of this file, the only which is used outside the file
    :param tosca_elements_map_to_provider: dict from provider specific file
    tosca_elements_map_to_<provider>.yaml
    :param node_templates: input node_templates
    :return: list of new node templates and relationship templates and
    list of artifacts to be used for generating scripts
    """
    element_templates = copy.copy(service_tmpl.node_templates)
    element_templates.update(copy.copy(service_tmpl.relationship_templates))

    new_element_templates = {}
    conditions = []
    self = dict()
    self[ARTIFACTS] = []
    self[EXTRA] = dict()

    for tmpl_name, element in element_templates.items():
        (namespace, _, _) = utils.tosca_type_parse(element[TYPE])
        self[NAME] = tmpl_name
        self[KEYNAME] = tmpl_name
        self[BUFFER] = {}

        if namespace != service_tmpl.provider:
            restructured_mapping = restructure_mapping(service_tmpl, element, tmpl_name, self)
            restructured_mapping = restructure_mapping_buffer(restructured_mapping, self)
            restructured_mapping, extra_mappings, new_conditions = restructure_mapping_facts(
                restructured_mapping, self)
            restructured_mapping.extend(extra_mappings)
            conditions.extend(new_conditions)
            restructured_mapping = restructure_get_attribute(restructured_mapping, service_tmpl, self)

            tpl_structure = translate_node_from_tosca(restructured_mapping, tmpl_name, self)
            for tpl_name, temp_tpl in tpl_structure.items():
                for node_type, tpl in temp_tpl.items():
                    (_, element_type, _) = utils.tosca_type_parse(node_type)
                    tpl[TYPE] = node_type
                    new_element_templates[element_type] = new_element_templates.get(element_type, {})
                    new_element_templates[element_type].update({tpl_name: copy.deepcopy(tpl)})
        else:
            new_element = translate_element_from_provider(tmpl_name, element)
            new_element_templates = utils.deep_update_dict(new_element_templates, new_element)

    conditions = set(conditions)
    self_extra = replace_brackets(self[EXTRA], False)
    self_artifacts = replace_brackets(self[ARTIFACTS], False)

    # REMOVE
    return new_element_templates, self_artifacts, conditions, self_extra

