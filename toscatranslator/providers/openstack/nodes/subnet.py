from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackSubnetNode(ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = 'Create subnet'
    ANSIBLE_MODULE = 'os_subnet'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackSubnetNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackSubnetNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
