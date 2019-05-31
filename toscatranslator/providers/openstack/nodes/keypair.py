from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackKeypairNode (ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = "Create keypair"
    ANSIBLE_MODULE = 'os_keypair'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackKeypairNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackKeypairNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
