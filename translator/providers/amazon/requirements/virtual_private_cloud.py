from translator.providers.amazon.nodefilters.virtual_private_cloud import AmazonVirtualPrivateCloudNodeFilter
from translator.common.requirement import ProviderRequirement


class AmazonVirtualPrivateCloudRequirement(ProviderRequirement):

    NAME = 'vpc'
    NODE_FILTER = AmazonVirtualPrivateCloudNodeFilter

    def __init__(self, data):
        super(AmazonVirtualPrivateCloudRequirement, self).__init__(data)
        self.filter()
