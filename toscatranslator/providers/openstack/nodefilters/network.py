from toscatranslator.common.nodefilter import ProviderNodeFilter


class OpenstackNetworkNodeFilter(ProviderNodeFilter):
    FACTS_KEY = "networks"

    def __init__(self):
        super(OpenstackNetworkNodeFilter, self).__init__()
