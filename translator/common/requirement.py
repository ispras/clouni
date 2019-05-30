from translator.common.exception import FulfillRequirementError
from toscaparser.common.exception import ExceptionCollector


class ProviderRequirement (object):

    CAPABILITY_NAME = 'self'

    def __init__(self, data):
        self.data = data
        self.name = None
        self.id = None

    def filter(self):
        # NOTE: only node_filter supported
        self.data = self.data.get('node_filter', {})
        self.name = self.data.get('properties', {}).get('name')
        self.name = self.data.get('capabilities', {}).get(self.CAPABILITY_NAME, {}).get('properties', {}).get('name') \
            if not self.name else self.name
        self.id = self.data.get('properties', {}).get('id')
        self.id = self.data.get('capabilities', {}).get(self.CAPABILITY_NAME, {}).get('properties', {}).get('id') \
            if not self.id else self.id
        if self.NODE_FILTER and not self.name and not self.id:
            node_filter = self.NODE_FILTER()
            node_filter.get_name_or_id(self)

        if not self.name and not self.id:
            raise ExceptionCollector.appendException(FulfillRequirementError(
                what=self.NAME
            ))

    def to_ansible(self):
        name_or_id = self.id if self.id else self.name
        return name_or_id
