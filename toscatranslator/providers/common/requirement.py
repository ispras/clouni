from toscatranslator.common.exception import UnavailableNodeFilterError, ValueType
from toscaparser.common.exception import ExceptionCollector

from toscatranslator.common.tosca_reserved_keys import REQUIREMENT_DEFAULT_PARAMS, RELATIONSHIP, \
    NAME_SUFFIX, ID_SUFFIX, NAME, ID, NODE_FILTER, CAPABILITIES, PROPERTIES, GET_FUNCTIONS

import six, copy


class ProviderRequirement (object):

    DEFAULT_REQUIRED_PARAMS = list(REQUIREMENT_DEFAULT_PARAMS)

    def __init__(self, provider, name, key, data, node_filter_key=None):
        self.provider = provider
        self.name = name
        self.key = key
        self.data = data
        self.relationship = self.data.get(RELATIONSHIP)
        self.node_filter_key = node_filter_key
        self.value = None

        self.requires = copy.deepcopy(self.DEFAULT_REQUIRED_PARAMS)
        if self.name[-5:] == NAME_SUFFIX:
            self.requires = [NAME]
        elif self.name[-3:] == ID_SUFFIX:
            self.requires = [ID]
        self.requires.append(self.name)

        self.filter()

    def filter(self):
        """
        Search for required parameters
        :return:
        """
        # NOTE: only node_filter supported
        data = self.data.get(NODE_FILTER)
        if data is None:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.name
            ))
        capabilities = data.get(CAPABILITIES, []) # is the list as the requirements
        properties = data.get(PROPERTIES, [])
        if not isinstance(capabilities, list):
            ExceptionCollector.appendException(ValueType(
                what="requirements: " + self.name + ": node_filter: capabilities",
                type="list"
            ))
        if not isinstance(properties, list):
            ExceptionCollector.appendException(ValueType(
                what="requirements: " + self.name + ": node_filter: properties",
                type="list"
            ))

        for requires in self.requires:
            for prop in properties:
                temp_value = prop.get(requires)
                if temp_value is not None:
                    self.value = temp_value
                    return

            for cap in capabilities:
                for cap_name, cap_val in cap.items():
                    cap_props = cap_val.get(PROPERTIES, [])
                    for prop in cap_props:
                        temp_value = prop.get(requires)
                        if temp_value is not None:
                            self.value = temp_value
                            return

        if not self.value:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.name,
                param=self.requires,
                data=data
            ))

    def get_value(self):
        return self.value

    def if_contain_get_function(self, value):
        if isinstance(value, six.string_types):
            return False
        if isinstance(value, dict):
            for k, v in value.items():
                if k in GET_FUNCTIONS:
                    return True
                if self.if_contain_get_function(v):
                    return True
            return False
        if isinstance(value, list):
            for v in value:
                if self.if_contain_get_function(v):
                    return True
            return False
        return False