from translator.providers.openstack.nodefilters.image import OpenstackImageNodeFilter
from translator.common.requirement import ProviderRequirement


class OpenstackImageRequirement(ProviderRequirement):

    NAME = 'image'
    NODE_FILTER = OpenstackImageNodeFilter

    def __init__(self, data):
        super(OpenstackImageRequirement, self).__init__(data)
        self.filter()
