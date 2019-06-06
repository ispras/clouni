from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackFloatingIpNode(ProviderResource):

    PRIORITY = 3
    ANSIBLE_DESCRIPTION = 'Create floating ip'
    ANSIBLE_MODULE = 'os_floating_ip'
