from toscatranslator.common.requirement import ProviderRequirement
from toscatranslator.common.exception import UnavailableNodeFilterError
from toscaparser.common.exception import ExceptionCollector


class AmazonSecurityGroupRequirement(ProviderRequirement):

    NAME = 'security_group'
    NODE_FILTER = None

    def __init__(self, data):
        super(AmazonSecurityGroupRequirement, self).__init__(data)

        self.name = self.data.get('node_filter', {}).get('properties', {}).get('name')
        if not self.name:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.NAME,
                param='name'
            ))
