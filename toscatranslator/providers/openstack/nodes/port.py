from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackPortNode(ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = 'Create port'
    ANSIBLE_MODULE = 'os_port'

