from toscatranslator.providers.common.provider_resource import ProviderResource


class AmazonInstanceNode(ProviderResource):

    PRIORITY = 3
    ANSIBLE_DESCRIPTION = 'Create instance'
    ANSIBLE_MODULE = 'ec2_instance'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonInstanceNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonInstanceNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
