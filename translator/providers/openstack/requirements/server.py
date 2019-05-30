from translator.common.requirement import ProviderRequirement
from translator.providers.openstack.nodefilters.server import OpenstackServerNodeFilter


class OpenstackServerRequirement(ProviderRequirement):

    NAME = 'server'
    NODE_FILTER = OpenstackServerNodeFilter

    def __init__(self, data):
        super(OpenstackServerRequirement, self).__init__(data)
        self.filter()