from toscatranslator.providers.openstack.nodefilters.subnet import OpenstackSubnetNodeFilter
from toscatranslator.common.requirement import ProviderRequirement


class OpenstackSubnetRequirement(ProviderRequirement):

    NAME = 'subnet'
    NODE_FILTER = OpenstackSubnetNodeFilter

    def __init__(self, data):
        super(OpenstackSubnetRequirement, self).__init__(data)
        self.filter()
