from toscatranslator.providers.common.nodefilter import ProviderNodeFilter


class OpenstackImageNodeFilter(ProviderNodeFilter):
    FACTS_KEY = "images"

    def __init__(self):
        super(OpenstackImageNodeFilter, self).__init__()
