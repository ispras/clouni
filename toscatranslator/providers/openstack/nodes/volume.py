from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackVolumeNode (ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = "Create volume"
    ANSIBLE_MODULE = 'os_volume'
