from toscatranslator.providers.common.nodefilter import ProviderNodeFilter


class OpenstackFlavorNodeFilter(ProviderNodeFilter):
    FACTS_KEY = 'flavors'

    def __init__(self):
        super(OpenstackFlavorNodeFilter, self).__init__()
