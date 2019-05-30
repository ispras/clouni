from translator.common.provider_resource import ProviderResource


class OpenstackFloatingIpNode(ProviderResource):

    PRIORITY = 3
    ANSIBLE_DESCRIPTION = 'Create floating ip'
    ANSIBLE_MODULE = 'os_floating_ip'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackFloatingIpNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackFloatingIpNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
