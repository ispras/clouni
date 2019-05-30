from translator.common.nodefilter import ProviderNodeFilter


class OpenstackPortNodeFilter (ProviderNodeFilter):
    FACTS_KEY = "ports"

    def __init__(self):
        super(OpenstackPortNodeFilter, self).__init__()
