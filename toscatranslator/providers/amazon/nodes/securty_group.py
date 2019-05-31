from toscatranslator.providers.common.provider_resource import ProviderResource


class AmazonSecurityGroupNode(ProviderResource):

    PRIORITY = 1
    ANSIBLE_DESCRIPTION = 'Create security group'
    ANSIBLE_MODULE = 'ec2_group'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonSecurityGroupNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonSecurityGroupNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
