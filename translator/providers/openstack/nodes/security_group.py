from translator.common.provider_resource import ProviderResource


class OpenstackSecurityGroupNode (ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = "Create security_group"
    ANSIBLE_MODULE = 'os_security_group'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super (OpenstackSecurityGroupNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackSecurityGroupNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
