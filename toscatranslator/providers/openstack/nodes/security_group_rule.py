from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackSecurityGroupRuleNode (ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = "Create security group rule"
    ANSIBLE_MODULE = 'os_security_group_rule'
