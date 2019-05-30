from translator.common.nodefilter import ProviderNodeFilter


class AmazonImageNodeFilter(ProviderNodeFilter):

    FACTS_KEY = 'ec2_ami_facts'

    def __init__(self):
        super(AmazonImageNodeFilter, self).__init__()
