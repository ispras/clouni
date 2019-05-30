from translator.common.provider_resource import ProviderResource


class OpenstackPortNode(ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = 'Create port'
    ANSIBLE_MODULE = 'os_port'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackPortNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackPortNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
