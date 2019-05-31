from toscatranslator.providers.common.provider_resource import ProviderResource


class OpenstackServerNode (ProviderResource):

    PRIORITY = 2
    ANSIBLE_DESCRIPTION = "Create instance"
    ANSIBLE_MODULE = 'os_server'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackServerNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackServerNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
