from toscatranslator.common.provider_resource import ProviderResource


class OpenstackRouterNode (ProviderResource):

    PRIORITY = 2
    ANSIBLE_DESCRIPTION = "Create router"
    ANSIBLE_MODULE = 'os_router'
    PROVIDER = 'openstack'

    def __init__(self, node):
        super(OpenstackRouterNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(OpenstackRouterNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
