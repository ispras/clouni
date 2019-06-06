from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackSecurityGroupNode (ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = "Create security_group"
    ANSIBLE_MODULE = 'os_security_group'
