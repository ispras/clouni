from translator.providers.amazon.requirements.elastic_network_interface import AmazonElasticNetworkInterfaceRequirement
from translator.providers.amazon.requirements.image import AmazonImageRequirement
from translator.providers.amazon.requirements.instance import AmazonInstanceRequirement
from translator.providers.amazon.requirements.security_group import AmazonSecurityGroupRequirement
from translator.providers.amazon.requirements.virtual_private_cloud import AmazonVirtualPrivateCloudRequirement
from translator.providers.amazon.requirements.virtual_private_cloud_subnet import AmazonVirtualPrivateCloudSubnetRequirement

from translator.common.all_requirements import ProviderRequirements


class AmazonRequirements(ProviderRequirements):
    REQUIREMENTS_OF_TYPE_LIST = {'network', 'security_groups'}

    BINDABLE = AmazonInstanceRequirement  # TODO
    ENI = AmazonElasticNetworkInterfaceRequirement
    IMAGE = AmazonImageRequirement
    INSTANCE = AmazonInstanceRequirement
    SECURITY_GROUP = AmazonSecurityGroupRequirement
    SUBNET = AmazonVirtualPrivateCloudSubnetRequirement
    VPC = AmazonVirtualPrivateCloudRequirement

    get = dict(
        device_id=BINDABLE,
        image_id=IMAGE,
        network=ENI,
        security_groups=SECURITY_GROUP,
        subnet_id=SUBNET,
        vpc_id=VPC
    )
