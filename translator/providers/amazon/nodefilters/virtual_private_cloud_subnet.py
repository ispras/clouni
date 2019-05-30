from translator.common.nodefilter import ProviderNodeFilter


class AmazonVirtualPrivateCloudSubnetNodeFilter(ProviderNodeFilter):

    FACTS_KEY = 'ec2_subnet_facts'

    def __init__(self):
        super(AmazonVirtualPrivateCloudSubnetNodeFilter, self).__init__()
