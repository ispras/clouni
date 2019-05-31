from toscatranslator.providers.openstack.nodefilters.network import OpenstackNetworkNodeFilter
from toscatranslator.common.requirement import ProviderRequirement


class OpenstackNetworkRequirement(ProviderRequirement):

    NAME = 'network'
    NODE_FILTER = OpenstackNetworkNodeFilter

    def __init__(self, data):
        super(OpenstackNetworkRequirement, self).__init__(data)
        self.filter()
