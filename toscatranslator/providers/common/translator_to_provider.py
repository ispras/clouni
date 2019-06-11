from toscatranslator.common import tosca_type
from toscaparser.common.exception import ExceptionCollector, ValidationError
from toscatranslator.common.exception import UnsupportedToscaParameterUsage, ToscaParametersMappingFailed, \
    UnsupportedMappingFunction

import copy
from netaddr import IPRange, IPAddress


SECTIONS = ('attributes', 'properties', 'capabilities', 'requirements', 'artifacts')
MAPPING_VALUE_KEYS = ('error', 'reason', 'parameter', 'value', 'condition', 'facts', 'arguments')
SUPPORTED_MAPPING_VALUE_STRUCTURE = (('error', 'reason'),
                                     ('parameter', 'value'),
                                     ('value', 'condition', 'facts', 'arguments'))
SEPARATOR = '.'


def contain_function(pool, argv):
    for obj in pool:
        if argv[1] in obj[argv[1]]:
            return obj
    return None


def equal_function(pool, argv):
    for obj in pool:
        if obj[argv[0]] == argv[1]:
            return obj
    return None


def ip_contain_function(pool, argv):
    param_start = argv[0]
    param_end = argv[1]
    addresses = argv[2]
    if not isinstance(addresses, list):
        ip_addresses = [IPAddress(addresses)]
    else:
        ip_addresses = [IPAddress(addr) for addr in addresses]

    for obj in pool:
        ip_start = obj[param_start]
        ip_end = obj[param_end]
        if isinstance(ip_start, str):
            ip_start = [ip_start]
            ip_end = [ip_end]
        num = min(len(ip_start), len(ip_end))
        for i in range(num):
            ip_range = IPRange(ip_start[i], ip_end[i])

            matched = True
            for ip_addr in ip_addresses:
                if ip_addr not in ip_range:
                    matched = False
                    break
            if matched:
                return obj

    return None


class ConditionFunction(object):
    GET_FUNCTION = dict(
        contains=contain_function,
        equals=equal_function,
        ip_contains=ip_contain_function
    )

    def __init__(self, name):
        self.name = name

    def get_function(self):
        return self.GET_FUNCTION.get(self.name)

    def valid(self):
        return self.get_function() is not None

    def supported(self):
        return self.GET_FUNCTION.keys()

    def execute(self, pool, argv):
        function_obj = self.get_function()
        return function_obj(pool, argv)


def translate_from_provider(node):
    node_templates = dict()
    node_templates[node.name] = node.entity_tpl
    return node_templates


def get_structure_of_mapped_param(mapped_params, value):
    if not isinstance(mapped_params, list):
        mapped_params = [mapped_params]

    for mapped_param in mapped_params:
        if isinstance(mapped_param, dict):
            value = next(iter(mapped_param.values()))
            mapped_param = next(iter(mapped_param.keys()))
        splitted = mapped_param.split(SEPARATOR)
        num = len(splitted)
        for i in range(num):
            if splitted[i] in SECTIONS:
                node_type = SEPARATOR.join(splitted[:i])
                cur_section = splitted[i]
                parameter_structure = value
                for k in range(num-1, i, -1):
                    temp = dict()
                    temp[splitted[k]] = parameter_structure
                    parameter_structure = temp

                structure = dict()
                structure[node_type] = dict()
                structure[node_type][cur_section] = parameter_structure
                return structure
    return None


def restructure_value(mapping_value, self, facts):
    if isinstance(mapping_value, dict):
        flat_mapping_value = dict()
        for key in MAPPING_VALUE_KEYS:
            mapping_sub_value = mapping_value.get(key)
            if mapping_sub_value is not None:
                flat_mapping_value[key] = restructure_value(mapping_sub_value, self, facts)

        # NOTE: the case when value has keys 'error' and 'reason'
        if flat_mapping_value.get('error', False):
            ExceptionCollector.appendException(UnsupportedToscaParameterUsage(
                what=flat_mapping_value.get('reason') % self
            ))

        # NOTE: the case when value has keys 'parameter' and 'value'
        parameter = flat_mapping_value.get('parameter')
        value = flat_mapping_value.get('value')
        if value is None:
            ExceptionCollector.appendException(ToscaParametersMappingFailed(
                what=parameter
            ))
            return

        if parameter is not None:
            r = dict()
            r[parameter] = value
            return r

        # NOTE: the case when value has keys 'value', 'condition', 'facts', 'arguments'
        condition_name = flat_mapping_value.get('condition')
        fact_name = flat_mapping_value.get('facts')
        arguments = flat_mapping_value.get('arguments')
        if condition_name is None or fact_name is None or arguments is None:
            ExceptionCollector.appendException(ToscaParametersMappingFailed(
                what=condition_name
            ))
            return
        pool = facts.get(fact_name)
        if pool is None:
            ExceptionCollector.appendException(ToscaParametersMappingFailed(
                what=pool
            ))
        function = ConditionFunction(condition_name)
        if not function.valid():
            ExceptionCollector.appendException(UnsupportedMappingFunction(
                what=condition_name,
                supported=function.supported()
            ))
        result = function.execute(pool, arguments)
        r = result.get(value)
        if r is None:
            ExceptionCollector.appendException(ToscaParametersMappingFailed(
                what=condition_name
            ))
        return r

    elif isinstance(mapping_value, list):
        return [restructure_value(v, self, facts) for v in mapping_value]

    if isinstance(mapping_value, str):
        mapping_value = mapping_value % self

    return mapping_value


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
    if is_matched_mapping_value(mapping_value):

        return dict(
            parameter=parameter,
            map=mapping_value,
            value=value
        )

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
        # if not r:
        #     ExceptionCollector.appendException(ToscaParametersMappingFailed(
        #         what=parameter
        #     ))
        return r

    if isinstance(value, list):
        r = []
        for v in value:
            item = get_restructured_mapping_item(key_prefix, parameter, mapping_value, v)
            # if not item:
            #     ExceptionCollector.appendException(ToscaParametersMappingFailed(
            #         what=parameter
            #     ))
            if isinstance(item, list):
                r.extend(item)
            elif item is not None:
                r.append(item)
        return r

    return None


def restructure_mapping(tosca_elements_map_to_provider, node):
    template = {}
    for section in SECTIONS:
        section_value = node.entity_tpl.get(section)
        if section_value is not None:
            template[section] = section_value

    return get_restructured_mapping_item('', '', tosca_elements_map_to_provider, value={node.type: template})


def translate_from_tosca(restructured_mapping, facts):
    """
    Translator from TOSCA definitions in provider definitions using rules from element_map_to_provider
    :param restructured_mapping: list of dict(parameter, map, value)
    :param facts: dict
    :return: entity_tpl as dict
    """
    resulted_structure = {}
    for item in restructured_mapping:
        ExceptionCollector.start()
        mapped_param = restructure_value(
            mapping_value=item['map'],
            self=dict(
                parameter=item['parameter'],
                value=item['value']
            ),
            facts=facts
        )
        ExceptionCollector.stop()
        if ExceptionCollector.exceptionsCaught():
            raise ValidationError(
                message='Translating to provider failed'
                    .join(ExceptionCollector.getExceptionsReport())
            )
        structure = get_structure_of_mapped_param(mapped_param, item['value'])

        # NOTE: 3 level update of dict
        for node_type, tpl in structure.items():
            temp_tpl = resulted_structure.get(node_type)
            if not temp_tpl:
                resulted_structure[node_type] = tpl
            else:
                for section, params in tpl.items():
                    temp_params = temp_tpl.get(section)
                    if not temp_params:
                        resulted_structure[node_type][section] = temp_params
                    else:
                        resulted_structure[node_type][section].update(temp_params)

    return resulted_structure


def translate(tosca_elements_map_to_provider, node_templates, facts):
    new_node_templates = {}
    for node in node_templates:
        (namespace, _, _) = tosca_type.parse(node.type)
        if namespace == 'tosca':
            restructured_mapping = restructure_mapping(tosca_elements_map_to_provider, node)
            tpl_structure = translate_from_tosca(restructured_mapping, facts)
            temp_node_templates = {}
            for node_type, tpl in tpl_structure.items():
                (_, _, type_name) = tosca_type.parse(node_type)
                node_name = node.name + '_' + type_name.lower()
                tpl['type'] = node_type
                temp_node_templates[node_name] = tpl
        else:
            temp_node_templates = translate_from_provider(node)

        for k, v in temp_node_templates.items():
            new_node_templates[k] = copy.deepcopy(v)

    return new_node_templates
