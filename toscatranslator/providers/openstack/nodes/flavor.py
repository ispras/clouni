from toscatranslator.common.provider_resource import ProviderResource


class OpenstackFlavorNode(ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create flavor'
    ANSIBLE_MODULE = 'os_flavor'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackFlavorNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackFlavorNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
