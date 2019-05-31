from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackNetworkNode(ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create network'
    ANSIBLE_MODULE = 'os_network'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackNetworkNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackNetworkNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
