from toscatranslator.common import snake_case

from toscatranslator.providers.common.provider_resource import ProviderResource
from toscatranslator.common.tosca_reserved_keys import AMAZON


class AmazonProviderResource(ProviderResource):
    NODE_PRIORITY_BY_TYPE = dict(
        ElasticIP=4,
        ElasticNetworkInterface=2,
        Image=0,
        Instance=3,
        SecurityGroup=1,
        VirtualPrivateCloud=0,
        VirtualPrivateCloudSubnet=1
    )

    ANSIBLE_DESCRIPTION_PREFIX = 'Create '
    ANSIBLE_MODULE_BY_TYPE = dict(
        ElasticIP='ec2_eip',
        ElasticNetworkInterface='ec2_eni',
        Image='ec2_ami',
        Instance='ec2_instance',
        SecurityGroup='ec2_group',
        VirtualPrivateCloud='ec2_vpc_net',
        VirtualPrivateCloudSubnet='ec2_vpc_subnet'
    )

    PROVIDER = AMAZON

    def ansible_description_by_type(self):
        desc = self.ANSIBLE_DESCRIPTION_PREFIX + snake_case.convert(self.type_name)
        return desc

    def ansible_module_by_type(self):
        name = self.ANSIBLE_MODULE_BY_TYPE.get(self.type_name)
        return name