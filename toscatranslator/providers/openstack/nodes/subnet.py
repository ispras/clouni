from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackSubnetNode(ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = 'Create subnet'
    ANSIBLE_MODULE = 'os_subnet'
