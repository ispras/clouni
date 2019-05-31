from toscatranslator.providers.common.nodefilter import ProviderNodeFilter


class OpenstackSubnetNodeFilter (ProviderNodeFilter):
    FACTS_KEY = "subnets"

    def __init__(self):
        super(OpenstackSubnetNodeFilter, self).__init__()
