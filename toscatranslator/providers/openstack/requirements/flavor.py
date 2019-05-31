from toscatranslator.providers.openstack.nodefilters.flavor import OpenstackFlavorNodeFilter
from toscatranslator.providers.common.requirement import ProviderRequirement


class OpenstackFlavorRequirement(ProviderRequirement):

    NAME = 'flavor'
    NODE_FILTER = OpenstackFlavorNodeFilter

    def __init__(self, data):
        super(OpenstackFlavorRequirement, self).__init__(data)
        self.filter()
