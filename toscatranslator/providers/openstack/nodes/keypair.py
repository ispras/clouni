from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackKeypairNode (ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = "Create keypair"
    ANSIBLE_MODULE = 'os_keypair'
