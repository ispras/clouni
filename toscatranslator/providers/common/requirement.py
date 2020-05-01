from toscatranslator.common.exception import UnavailableNodeFilterError
from toscaparser.common.exception import ExceptionCollector

from toscatranslator.common.tosca_reserved_keys import REQUIREMENT_DEFAULT_PARAMS, RELATIONSHIP, \
    NAME_SUFFIX, ID_SUFFIX, NAME, ID, NODE_FILTER, CAPABILITIES, PROPERTIES, GET_FUNCTIONS

import six


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

        self.requires = self.DEFAULT_REQUIRED_PARAMS
        if self.name[-5:] == NAME_SUFFIX:
            self.requires = [NAME]
        elif self.name[-3:] == ID_SUFFIX:
            self.requires = [ID]

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
        capabilities = data.get(CAPABILITIES, {})
        for requires in self.requires:
            temp_value = data.get(PROPERTIES, {}).get(requires)
            if temp_value is not None:
                self.value = temp_value
                return

            for cap_name, cap_val in capabilities.items():
                temp_value = cap_val.get(PROPERTIES, {}).get(requires)
                if temp_value is not None:
                    self.value = temp_value
                    return

        if not self.value:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.name,
                param=self.requires
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