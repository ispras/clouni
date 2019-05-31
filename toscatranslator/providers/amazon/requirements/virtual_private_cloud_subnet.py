from toscatranslator.providers.amazon.nodefilters.virtual_private_cloud_subnet import AmazonVirtualPrivateCloudSubnetNodeFilter
from toscatranslator.providers.common.requirement import ProviderRequirement


class AmazonVirtualPrivateCloudSubnetRequirement(ProviderRequirement):

    NAME = 'subnet'
    NODE_FILTER = AmazonVirtualPrivateCloudSubnetNodeFilter

    def __init__(self, data):
        super(AmazonVirtualPrivateCloudSubnetRequirement, self).__init__(data)
        self.filter()
