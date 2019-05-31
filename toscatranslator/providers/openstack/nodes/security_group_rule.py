from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackSecurityGroupRuleNode (ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = "Create security group rule"
    ANSIBLE_MODULE = 'os_security_group_rule'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackSecurityGroupRuleNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackSecurityGroupRuleNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
