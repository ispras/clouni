from translator.common.provider_resource import ProviderResource


class AmazonElasticNetworkInterfaceNode(ProviderResource):

    PRIORITY = 2
    ANSIBLE_DESCRIPTION = 'Create elastic network interface'
    ANSIBLE_MODULE = 'ec2_eni'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonElasticNetworkInterfaceNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonElasticNetworkInterfaceNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
