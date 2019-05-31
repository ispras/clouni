from toscatranslator.providers.common.requirement import ProviderRequirement
from toscatranslator.common.exception import UnavailableNodeFilterError
from toscaparser.common.exception import ExceptionCollector


class AmazonInstanceRequirement(ProviderRequirement):

    NAME = 'instance'
    NODE_FILTER = None

    def __init__(self, data):
        super(AmazonInstanceRequirement, self).__init__(data)

        self.name = self.data.get('node_filter', {}).get('properties', {}).get('name')
        if not self.name:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.NAME,
                param='name'
            ))
