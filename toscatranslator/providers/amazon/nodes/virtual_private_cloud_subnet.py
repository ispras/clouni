from toscatranslator.providers.common.provider_resource import ProviderResource


class AmazonVirtualPrivateCloudSubnetNode(ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = 'Create subnet'
    ANSIBLE_MODULE = 'ec2_vpc_subnet'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonVirtualPrivateCloudSubnetNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonVirtualPrivateCloudSubnetNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
