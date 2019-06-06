from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackImageNode (ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create image'
    ANSIBLE_MODULE = 'os_image'
