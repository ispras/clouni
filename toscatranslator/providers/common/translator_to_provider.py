from toscatranslator.common.utils import execute_function
from toscatranslator.common import tosca_type
from toscatranslator.common import snake_case
from toscaparser.common.exception import ExceptionCollector, ValidationError
from toscatranslator.common.exception import UnsupportedToscaParameterUsage, ToscaParametersMappingFailed, \
    UnsupportedExecutorType
from toscatranslator.common.tosca_reserved_keys import *
from toscatranslator.configuration_tools.combined.combine_configuration_tools import CONFIGURATION_TOOLS

import copy
import six

from random import randint, seed
from time import time

from toscatranslator.common.utils import deep_update_dict

SEPARATOR = '.'
MAP_KEY = "map"
SET_FACT_SOURCE = "set_fact"
INDIVISIBLE_KEYS = [GET_OPERATION_OUTPUT, INPUTS, IMPLEMENTATION]

ARTIFACT_RANGE_START = 1000
ARTIFACT_RANGE_END = 9999
PYTHON_EXECUTOR = 'python'
PYTHON_SOURCE_DIRECTORY = 'toscatranslator.providers.common.python_sources'


def translate_element_from_provider(node):
    (_, element_type, _) = tosca_type.parse(node.type)
    node_templates = {
        element_type: {
            node.name: copy.deepcopy(node.entity_tpl)
        }
    }
    return node_templates


def get_structure_of_mapped_param(mapped_param, value, self=None, type_list_parameters=None, indivisible=False):
    if mapped_param is None:
        # NOTE The case when parameter was 'self'
        return [], None
    if self is None:
        self = value

    if type_list_parameters is None:
        type_list_parameters = []

    if isinstance(mapped_param, str):
        splitted_mapped_param = mapped_param.split(SEPARATOR)
        if splitted_mapped_param[-1] in INDIVISIBLE_KEYS:
            indivisible = True
        if not indivisible:
            if isinstance(value, list):
                r = []
                len_v = len(value)
                if len_v == 1:
                    type_list_parameters.append(len(mapped_param.split(SEPARATOR)))
                    param, _ = get_structure_of_mapped_param(mapped_param, value[0], self, type_list_parameters)
                    return param, None

                for v in value:
                    if isinstance(v, str):
                        param, _ = get_structure_of_mapped_param(SEPARATOR.join([mapped_param, v]), self, self,
                                                                 type_list_parameters)
                    else:
                        param, _ = get_structure_of_mapped_param(mapped_param, v, self, type_list_parameters)
                    r += param
                return r, None

            if isinstance(value, dict):
                r = []
                for k, v in value.items():
                    param, _ = get_structure_of_mapped_param(SEPARATOR.join([mapped_param, k]), v, self,
                                                             type_list_parameters)
                    r += param
                return r, None

        # NOTE: end of recursion
        num = len(splitted_mapped_param)

        structure = dict()
        for i in range(num):
            if splitted_mapped_param[i] in NODE_TEMPLATE_KEYS:
                node_type = SEPARATOR.join(splitted_mapped_param[:i])
                cur_section = splitted_mapped_param[i]
                parameter_structure = value
                if num in type_list_parameters:
                    parameter_structure = [value]
                for k in range(num - 1, i, -1):
                    temp = dict()
                    temp[splitted_mapped_param[k]] = parameter_structure
                    if k in type_list_parameters:
                        temp = [temp]
                    parameter_structure = temp

                structure[node_type] = dict()
                if cur_section == REQUIREMENTS:
                    parameter_structure = [parameter_structure]
                structure[node_type][cur_section] = parameter_structure
                return [structure], None

        # NOTE: Case when node has no parameters but needed
        ExceptionCollector.appendException(ToscaParametersMappingFailed(
            what=mapped_param
        ))
        structure[mapped_param] = dict()
        return [structure], None

    if isinstance(mapped_param, list):
        r = []
        for p in mapped_param:
            param, _ = get_structure_of_mapped_param(p, value, self, type_list_parameters)
            r += param
        return r, None

    if isinstance(mapped_param, dict):
        # NOTE: Assert number of keys! Always start of recursion?
        # TODO add keyname
        # TODO check with private address as it has multiple
        num_of_keys = len(mapped_param.keys())
        # if mapped_param.get(PARAMETER) and (num_of_keys == 2 or num_of_keys == 3 and KEYNAME in mapped_param.keys()):
        if num_of_keys == 1 or num_of_keys == 2 and KEYNAME in mapped_param.keys():
            for k, v in mapped_param.items():
                if k != PARAMETER and k != KEYNAME:
                    param, _ = get_structure_of_mapped_param(k, v, self, type_list_parameters)
                    if isinstance(param, tuple):
                        (param, keyname) = param
                        if mapped_param.get(KEYNAME):
                            mapped_param[KEYNAME] = keyname
                    return param, mapped_param.get(KEYNAME)
        else:
            # TODO find the cases
            assert False

    ExceptionCollector.appendException(ToscaParametersMappingFailed(
        what=mapped_param
    ))


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
                restructured_value = restructure_value(mapping_sub_value, self, key != PARAMETER, False)
                if restructured_value is None:
                    ExceptionCollector.appendException(ToscaParametersMappingFailed(
                        what=mapping_value
                    ))
                    return
                flat_mapping_value[key] = restructured_value

        # NOTE: the case when value has keys ERROR and REASON
        if flat_mapping_value.get(ERROR, False):
            ExceptionCollector.appendException(UnsupportedToscaParameterUsage(
                what=flat_mapping_value.get(REASON).format(self=self)
            ))

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
                ExceptionCollector.appendException(ToscaParametersMappingFailed(
                    what=parameter
                ))
            if parameter[:6] == '{self[' and parameter.index('}') == len(parameter) - 1:
                # The case when variable is written to the parameter self!
                params_parameter = parameter[6:-2].split('][')
                iter_value = value
                iter_num = len(params_parameter)
                for i in range(iter_num - 1, 0, -1):
                    temp_param = dict()
                    temp_param[params_parameter[i]] = iter_value
                    iter_value = temp_param
                self[params_parameter[0]] = deep_update_dict(self.get(params_parameter[0], {}), iter_value)
                return
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
                return execute_function(PYTHON_SOURCE_DIRECTORY, source_name, parameters_dict)
            if not CONFIGURATION_TOOLS.get(executor_name):
                ExceptionCollector.appendException(UnsupportedExecutorType(
                    what=executor_name
                ))
            if self.get(ARTIFACTS) is None:
                self[ARTIFACTS] = []

            tool = CONFIGURATION_TOOLS[executor_name]()
            extension = tool.get_artifact_extension()

            seed(time())
            artifact_name = '_'.join([self[NAME], executor_name, source_name,
                                      str(randint(ARTIFACT_RANGE_START, ARTIFACT_RANGE_END))]) + extension
            flat_mapping_value.update(
                name=artifact_name,
                configuration_tool=executor_name
            )
            self[ARTIFACTS].append(flat_mapping_value)
            # return the name of artifact
            return artifact_name

        ExceptionCollector.appendException(ToscaParametersMappingFailed(
            what=mapping_value
        ))
        return

    elif isinstance(mapping_value, list):
        return [restructure_value(v, self, if_upper=False) for v in mapping_value]

    if isinstance(mapping_value, str) and if_format_str:
        # NOTE: the process is needed because using only format function makes string from json
        if mapping_value[:6] == '{self[' and mapping_value.index('}') == len(mapping_value) - 1:
            mapping_value = mapping_value[6:-2]
            params_map_val = mapping_value.split('][')
            temp_val = self
            for param in params_map_val:
                temp_val = temp_val.get(param, {})
            return temp_val

        try:
            mapping_value = mapping_value.format(self=self)
        except ValueError:
            pass
    return mapping_value


def get_resulted_mapping_values(parameter, mapping_value, value):
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
     # NOTE at first check if parameter self[buffer] parameter
    if mapping_value_parameter and not (
            mapping_value_parameter[:6] == '{self[' and mapping_value_parameter.index('}') == len(
            mapping_value_parameter) - 1):
        splitted_mapping_value_parameter = mapping_value_parameter.split(SEPARATOR)
        has_section = False
        for v in splitted_mapping_value_parameter:
            if v in NODE_TEMPLATE_KEYS:
                has_section = True
                break
        if not has_section:
            mapping_value_value = mapping_value.get(VALUE)
            if isinstance(mapping_value_value, list) and len(mapping_value_value) > 1:
                r = []
                for v in mapping_value_value:
                    mapping_value[VALUE] = v
                    item = get_resulted_mapping_values(parameter, mapping_value, value)
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
                        # parameter_tag = SEPARATOR.join(splitted_mapping_value_value[:i+1])
                        # value_new = SEPARATOR.join(splitted_mapping_value_value[i-1:])
                        # mapping_value[PARAMETER] = mapping_value_parameter + SEPARATOR + parameter_tag
                        # mapping_value[VALUE] = value_new
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
                    r = get_resulted_mapping_values(parameter, mapping_value, value)
                    return r

            ExceptionCollector.appendException(ToscaParametersMappingFailed(
                what=mapping_value
            ))

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


def get_restructured_mapping_item(key_prefix, parameter, mapping_value, value):
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
            item = get_restructured_mapping_item(key_prefix, parameter, v, value)
            if isinstance(item, list):
                r.extend(item)
            elif item is not None:
                r.append(item)
        return r

    if is_matched_mapping_value(mapping_value):
        # NOTE: end of recursion, when parameter is found
        # ERROR floating_ip example, the value is the list but not
        resulted_mapping_values = get_resulted_mapping_values(parameter, mapping_value, value)
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
                item = get_restructured_mapping_item(arg_key_prefix, arg_parameter, arg_map, v)
                if isinstance(item, list):
                    r.extend(item)
                elif item is not None:
                    r.append(item)
        return r

    if isinstance(value, list):
        r = []
        for v in value:
            item = get_restructured_mapping_item(key_prefix, parameter, mapping_value, v)
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
        item = get_restructured_mapping_item(arg_key_prefix, arg_parameter, arg_map, True)
        if isinstance(item, list):
            r.extend(item)
        elif item is not None:
            r.append(item)
        return r

    return None


def restructure_mapping(tosca_elements_map_to_provider, node):
    """
    Restructure the mapping elements to make the mapping uniform the only 1 version to be interpreted.
    Only assigned with value parameters are mentioned
    Restructured output is list of objects with keys: ('parameter', 'value', 'map'), parameter is a normative parameter,
        value is a value of normative parameter, map is a resulting specialized parameter:value map
    :param tosca_elements_map_to_provider: input mapping from file.yaml
    :param node: input node to be mapped
    :return: restructured_mapping: dict
    """
    template = {}
    for section in NODE_TEMPLATE_KEYS:
        section_value = node.entity_tpl.get(section)
        if section_value is not None:
            template[section] = section_value

    return get_restructured_mapping_item('', '', tosca_elements_map_to_provider, value={node.type: template})


def translate_node_from_tosca(restructured_mapping, tpl_name):
    """
    Translator from TOSCA definitions in provider definitions using rules from element_map_to_provider
    :param restructured_mapping: list of dicts(parameter, map, value)
    :param tpl_name: str
    :return: entity_tpl as dict
    """
    resulted_structure = {}
    self = dict()
    self[NAME] = tpl_name
    self[ARTIFACTS] = []

    for item in restructured_mapping:
        ExceptionCollector.start()
        self[PARAMETER] = item[PARAMETER]
        self[VALUE] = item[VALUE]
        mapped_param = restructure_value(
            mapping_value=item[MAP_KEY],
            self=self
        )
        ExceptionCollector.stop()
        if ExceptionCollector.exceptionsCaught():
            raise ValidationError(
                message='\nTranslating to provider failed: '
                    .join(ExceptionCollector.getExceptionsReport())
            )
        structures, keyname = get_structure_of_mapped_param(mapped_param, item[VALUE])

        # NOTE: 4 level update of dict
        for structure in structures:
            for node_type, tpl in structure.items():
                if not keyname:
                    (_, _, type_name) = tosca_type.parse(node_type)
                    keyname = self[NAME] + "_" + snake_case.convert(type_name)
                tpl_by_name = resulted_structure.get(keyname)
                if not tpl_by_name:
                    resulted_structure[keyname] = {
                        node_type: tpl
                    }
                else:
                    temp_tpl = tpl_by_name.get(node_type)
                    if not temp_tpl:
                        resulted_structure[keyname][node_type] = tpl
                    else:
                        for section, params in tpl.items():
                            temp_params = temp_tpl.get(section)
                            if not temp_params:
                                resulted_structure[keyname][node_type][section] = params
                            else:
                                if section == REQUIREMENTS:
                                    # NOTE params is of type list
                                    # resulted_structure[keyname][node_type][section] is of type list
                                    # Search for the same requirements
                                    left_params = copy.deepcopy(params)
                                    for i in range(len(resulted_structure[keyname][node_type][section])):
                                        r = resulted_structure[keyname][node_type][section][i]
                                        r_keys = set(r.keys())
                                        for j in range(len(params)):
                                            new = params[j]
                                            new_keys = set(new.keys())
                                            common = r_keys.intersection(new_keys)
                                            if bool(common):
                                                for v in common:
                                                    temp_v = resulted_structure[keyname][node_type][section][i][v]
                                                    resulted_structure[keyname][node_type][section][i][v] = \
                                                        deep_update_dict(temp_v, params[j][v])
                                                    left_params[j].pop(v)
                                                    if not bool(left_params[j]):
                                                        left_params = left_params[:j].extend(left_params[j + 1:])
                                                        # NOTE if empty list is extended with empty list it returns None without error
                                                        if not left_params:
                                                            left_params = []

                                    resulted_structure[keyname][node_type][section].extend(left_params)
                                else:
                                    if isinstance(params, list):
                                        for params_i in params:
                                            resulted_structure[keyname][node_type][section] = \
                                                deep_update_dict(temp_params, params_i)
                                    else:
                                        resulted_structure[keyname][node_type][section] = \
                                            deep_update_dict(temp_params, params)

    return resulted_structure, self[ARTIFACTS]


def get_source_structure_from_facts(condition, fact_name, value, arguments, executor, target_parameter,
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
        fact_name_splitted = fact_name.split(SEPARATOR)
        source_name = fact_name_splitted[0]
        facts_result = "facts_result"
        if len(fact_name_splitted) > 1:
            facts_result += "[\"" + "\"][\"".join(fact_name_splitted[1:]) + "\"]"
        facts_result = "{{{{ " + facts_result + " }}}}"
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
            }
        ]
    else:
        new_global_elements_map_total_implementation = fact_name

    target_parameter_splitted = target_parameter.split(SEPARATOR)
    relationship_name = "{self[name]}_server_" + snake_case.convert(target_parameter_splitted[-1])

    provider = target_parameter_splitted[0]
    target_interface_name = "Target"
    target_relationship_type = SEPARATOR.join([provider, RELATIONSHIPS, "DependsOn"])

    target_type = None
    target_short_parameter = None
    for i in range(len(target_parameter_splitted)):
        if target_parameter_splitted[i] in NODE_TEMPLATE_KEYS:
            target_type = SEPARATOR.join(target_parameter_splitted[:i])
            target_short_parameter = '_'.join(target_parameter_splitted[i:])
            break
    if not target_type or not target_short_parameter:
        ExceptionCollector.appendException(ToscaParametersMappingFailed(
            what=target_parameter
        ))

    tag_operation_name = None
    if isinstance(fact_name, six.string_types):
        tag_operation_name = fact_name.replace(SEPARATOR, '_')
    elif isinstance(fact_name, dict):
        for k, v in fact_name:
            tag_operation_name = k.replace(SEPARATOR, '_')
            break
    elif isinstance(fact_name, list):
        if isinstance(fact_name[0], dict):
            for k, v in fact_name[0].items():
                tag_operation_name = k.replace(SEPARATOR, '_')
                break
        else:
            tag_operation_name = str(fact_name[0]).replace(SEPARATOR, '_')
    else:
        tag_operation_name = str(fact_name).replace(SEPARATOR, '_')

    choose_operation_name = "choose_" + tag_operation_name
    total_operation_name = "total_" + tag_operation_name

    target_total_parameter_new = SEPARATOR.join([target_relationship_type, INTERFACES, target_interface_name,
                                                 total_operation_name])
    target_choose_parameter_new = SEPARATOR.join([target_relationship_type, INTERFACES, target_interface_name,
                                                  choose_operation_name])

    new_elements_map = {
        GET_OPERATION_OUTPUT: [
            relationship_name,
            target_interface_name,
            choose_operation_name,
            value
        ]
    }
    new_global_elements_map_total = {
        PARAMETER: target_total_parameter_new,
        KEYNAME: relationship_name,
        VALUE: {
            IMPLEMENTATION: new_global_elements_map_total_implementation
        }
    }
    new_global_elements_map_choose = {
        PARAMETER: target_choose_parameter_new,
        KEYNAME: relationship_name,
        VALUE: {
            IMPLEMENTATION: [
                condition + ".yaml",
                {
                    SOURCE: SET_FACT_SOURCE,
                    PARAMETERS: {
                        value: "{{{{ matched_object[\"" + value + "\"] }}}}"
                    },
                    VALUE: "tmp_value",
                    EXECUTOR: executor
                }
            ],
            INPUTS: {
                "input_facts": {
                    GET_OPERATION_OUTPUT: [
                        SELF,
                        target_interface_name,
                        total_operation_name,
                        "target_objects"
                    ]
                },
                "input_args": arguments
            }
        }
    }
    new_global_elements_map = [
        {
            PARAMETER: source_parameter,
            MAP_KEY: new_global_elements_map_choose,
            VALUE: source_value
        },
        {
            PARAMETER: source_parameter,
            MAP_KEY: new_global_elements_map_total,
            VALUE: source_value
        }
    ]

    return new_elements_map, new_global_elements_map


def restructure_mapping_facts(elements_map, extra_elements_map=None, target_parameter=None, source_parameter=None,
                              source_value=None):
    """
    Function is used to restructure mapping values with the case of `facts`, `condition`, `arguments`, `value` keys
    :param elements_map:
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
            cur_elements, extra_elements_map, new_conditions = restructure_mapping_facts(v, extra_elements_map,
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
                ExceptionCollector.appendException(ToscaParametersMappingFailed(
                    what=target_parameter
                ))

            input_parameter = new_elements_map[PARAMETER]
            input_value = new_elements_map[VALUE]
            input_keyname = new_elements_map.get(KEYNAME)

            provider = separated_target_parameter[0]
            target_relationship_type = SEPARATOR.join([provider, RELATIONSHIPS, "DependsOn"])
            relationship_name = "{self[name]}_server_" + snake_case.convert(separated_target_parameter[-1])

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
                                value_name: "{{{{ {{ input_parameter: input_value }} }}}}"
                                # so many braces because format
                                # uses braces and replace '{{' with '{'
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
            if executor not in CONFIGURATION_TOOLS.keys():
                ExceptionCollector.appendException(UnsupportedExecutorType(
                    what=executor
                ))
            new_elements_map, cur_extra_elements = get_source_structure_from_facts(condition, fact_name, value,
                                                                                   arguments,
                                                                                   executor,
                                                                                   target_parameter, source_parameter,
                                                                                   source_value)
            conditions.append(condition)
            extra_elements_map.extend(cur_extra_elements)

        return new_elements_map, extra_elements_map, conditions

    if isinstance(elements_map, list):
        new_elements_map = []
        for k in elements_map:
            cur_elements, extra_elements_map, new_conditions = restructure_mapping_facts(k, extra_elements_map,
                                                                                         target_parameter,
                                                                                         source_parameter, source_value)
            new_elements_map.append(cur_elements)
            conditions.extend(new_conditions)
        return new_elements_map, extra_elements_map, conditions

    return elements_map, extra_elements_map, conditions


def translate(tosca_elements_map_to_provider, topology_template):
    """
    Main function of this file, the only which is used outside the file
    :param tosca_elements_map_to_provider: dict from provider specific file
    tosca_elements_map_to_<provider>.yaml
    :param node_templates: input node_templates
    :return: list of new node templates and relationship templates and
    list of artifacts to be used for generating scripts
    """
    node_templates = topology_template.nodetemplates
    relationship_templates = topology_template.relationship_templates
    element_templates = node_templates + relationship_templates

    new_element_templates = {}
    artifacts = []
    conditions = []

    for element in element_templates:
        (namespace, _, _) = tosca_type.parse(element.type)
        if namespace == TOSCA:
            restructured_mapping = restructure_mapping(tosca_elements_map_to_provider, element)

            restructured_mapping, extra_mappings, conditions = restructure_mapping_facts(restructured_mapping)
            restructured_mapping.extend(extra_mappings)

            tpl_structure, artifacts = translate_node_from_tosca(restructured_mapping, element.name)
            for tpl_name, temp_tpl in tpl_structure.items():
                for node_type, tpl in temp_tpl.items():
                    (_, element_type, _) = tosca_type.parse(node_type)
                    tpl[TYPE] = node_type
                    new_element_templates[element_type] = new_element_templates.get(element_type, {})
                    new_element_templates[element_type].update({tpl_name: copy.deepcopy(tpl)})
        else:
            new_element = translate_element_from_provider(element)
            new_element_templates = deep_update_dict(new_element_templates, new_element)

        conditions = set(conditions)

    return new_element_templates, artifacts, conditions
