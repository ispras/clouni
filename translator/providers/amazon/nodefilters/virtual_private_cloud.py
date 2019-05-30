from translator.common.nodefilter import ProviderNodeFilter


class AmazonVirtualPrivateCloudNodeFilter(ProviderNodeFilter):

    FACTS_KEY = 'ec2_vpc_facts'

    def __init__(self):
        super(AmazonVirtualPrivateCloudNodeFilter, self).__init__()
