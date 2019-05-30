from translator.common.provider_resource import ProviderResource


class AmazonElasticIPNode(ProviderResource):

    PRIORITY = 4
    ANSIBLE_DESCRIPTION = 'Create elastic ip'
    ANSIBLE_MODULE = 'ec2_eip'
    PROVIDER = 'amazon'

    def __init__(self, node):
        super(AmazonElasticIPNode, self).__init__(node)

    def to_ansible(self):
        try:
            super(AmazonElasticIPNode, self).to_ansible()
        except NotImplementedError:
            pass
        return self.pb
