from toscatranslator.common.provider_resource import ProviderResource


class AmazonImageNode(ProviderResource):

    PRIORITY = 0
    ANSIBLE_DESCRIPTION = 'Create image'
    ANSIBLE_MODULE = 'ec2_ami'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonImageNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonImageNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
