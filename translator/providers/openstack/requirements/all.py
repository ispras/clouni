from translator.providers.openstack.requirements.flavor import OpenstackFlavorRequirement
from translator.providers.openstack.requirements.image import OpenstackImageRequirement
from translator.providers.openstack.requirements.network import OpenstackNetworkRequirement
from translator.providers.openstack.requirements.security_group import OpenstackSecurityGroupRequirement
from translator.providers.openstack.requirements.server import OpenstackServerRequirement
from translator.providers.openstack.requirements.subnet import OpenstackSubnetRequirement
from translator.providers.openstack.requirements.volume import OpenstackVolumeRequirement

from translator.common.all_requirements import ProviderRequirements


class OpenstackRequirements (ProviderRequirements):
    REQUIREMENTS_OF_TYPE_LIST = {"floating_ips", "interfaces", "nics", "security_groups", "volumes"}

    FLAVOR = OpenstackFlavorRequirement
    IMAGE = OpenstackImageRequirement
    NETWORK = OpenstackNetworkRequirement
    SECURITY_GROUP = OpenstackSecurityGroupRequirement
    SERVER = OpenstackServerRequirement
    SUBNET = OpenstackSubnetRequirement
    VOLUME = OpenstackVolumeRequirement

    get = dict(
        boot_volume=VOLUME,
        flavor=FLAVOR,
        image=IMAGE,
        interfaces=SUBNET,
        network=NETWORK,
        network_name=NETWORK,
        nics=NETWORK,
        security_group=SECURITY_GROUP,
        security_groups=SECURITY_GROUP,
        server=SERVER,
        snapshot_id=VOLUME,
        volumes=VOLUME
    )
