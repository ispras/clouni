from toscatranslator.common.provider_resource import ProviderResource


class AmazonVirtualPrivateCloudNode(ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create vpc'
    ANSIBLE_MODULE = 'ec2_vpc_net'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonVirtualPrivateCloudNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonVirtualPrivateCloudNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
