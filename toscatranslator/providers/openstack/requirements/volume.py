from toscatranslator.common.requirement import ProviderRequirement
from toscatranslator.common.exception import UnavailableNodeFilterError
from toscaparser.common.exception import ExceptionCollector


class OpenstackVolumeRequirement(ProviderRequirement):

    NAME = 'volume'

    def __init__(self, data):
        super(OpenstackVolumeRequirement, self).__init__(data)

        self.name = self.data.get('node_filter', {}).get('properties', {}).get('name')
        self.id = self.data.get('node_filter', {}).get('properties', {}).get('id')
        if not self.name and not self.id:
            ExceptionCollector.appendException(UnavailableNodeFilterError(
                what=self.NAME,
                param=('name', 'id')
            ))
