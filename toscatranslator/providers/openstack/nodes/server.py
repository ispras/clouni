from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackServerNode (ProviderResource):

    PRIORITY = 2
    ANSIBLE_DESCRIPTION = "Create instance"
    ANSIBLE_MODULE = 'os_server'
