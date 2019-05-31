from toscatranslator.common.nodefilter import ProviderNodeFilter


class OpenstackServerNodeFilter (ProviderNodeFilter):
    FACTS_KEY = "servers"

    def __init__(self):
        super(OpenstackServerNodeFilter, self).__init__()
