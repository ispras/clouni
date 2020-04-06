from toscatranslator.common.exception import FulfillRequirementError, UnavailableNodeFilterError
from toscaparser.common.exception import ExceptionCollector

from toscatranslator.providers.common.nodefilter import ProviderNodeFilter
from toscatranslator.providers.common.tosca_reserved_keys import REQUIREMENT_DEFAULT_PARAMS, RELATIONSHIP, \
    NAME_SUFFIX, ID_SUFFIX, NAME, ID, NODE_FILTER, CAPABILITIES, PROPERTIES


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
        self.data = self.data.get(NODE_FILTER)
        if self.data is None:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.name
            ))
        capabilities = self.data.get(CAPABILITIES, {})
        for requires in self.requires:
            self.value = self.data.get(PROPERTIES, {}).get(requires)
            if self.value:
                return

            for cap_name, cap_val in capabilities.items():
                self.value = cap_val.get(PROPERTIES, {}).get(requires)
                if self.value:
                    return

        if self.node_filter_key and not self.value:
            node_filter = ProviderNodeFilter(self.provider, self.node_filter_key)
            self.value = node_filter.get_required_value(self.data, self.requires)

        if not self.value:
            raise ExceptionCollector.appendException(FulfillRequirementError(
                what=self.name + ' = ' + str(self.data)
            ))

    def get_value(self):
        return self.value
