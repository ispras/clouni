from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackRouterNode (ProviderResource):

    PRIORITY = 2
    ANSIBLE_DESCRIPTION = "Create router"
    ANSIBLE_MODULE = 'os_router'
