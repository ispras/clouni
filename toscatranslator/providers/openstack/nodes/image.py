from toscatranslator.common.provider_resource import ProviderResource


class OpenstackImageNode (ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create image'
    ANSIBLE_MODULE = 'os_image'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackImageNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackImageNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
