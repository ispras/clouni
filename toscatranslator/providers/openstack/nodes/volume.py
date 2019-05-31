from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackVolumeNode (ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = "Create volume"
    ANSIBLE_MODULE = 'os_volume'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackVolumeNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackVolumeNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
