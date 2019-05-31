from toscatranslator.providers.common.nodefilter import ProviderNodeFilter


class AmazonElasticNetworkInterfaceNodeFilter(ProviderNodeFilter):

    FACTS_KEY = 'ec2_eni_facts'

    def __init__(self):
        super(AmazonElasticNetworkInterfaceNodeFilter, self).__init__()
