from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackNetworkNode(ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create network'
    ANSIBLE_MODULE = 'os_network'

