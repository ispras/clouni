from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackFlavorNode(ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create flavor'
    ANSIBLE_MODULE = 'os_flavor'
