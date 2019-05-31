from toscatranslator.providers.amazon.nodefilters.elastic_network_interface import AmazonElasticNetworkInterfaceNodeFilter
from toscatranslator.common.requirement import ProviderRequirement


class AmazonElasticNetworkInterfaceRequirement(ProviderRequirement):

    NAME = 'elastic_network_interface'
    NODE_FILTER = AmazonElasticNetworkInterfaceNodeFilter

    def __init__(self, data):
        super(AmazonElasticNetworkInterfaceRequirement, self).__init__(data)
        self.filter()
