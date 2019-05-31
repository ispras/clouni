from toscatranslator.providers.openstack.requirements.flavor import OpenstackFlavorRequirement
from toscatranslator.providers.openstack.requirements.image import OpenstackImageRequirement
from toscatranslator.providers.openstack.requirements.network import OpenstackNetworkRequirement
from toscatranslator.providers.openstack.requirements.security_group import OpenstackSecurityGroupRequirement
from toscatranslator.providers.openstack.requirements.server import OpenstackServerRequirement
from toscatranslator.providers.openstack.requirements.subnet import OpenstackSubnetRequirement
from toscatranslator.providers.openstack.requirements.volume import OpenstackVolumeRequirement

from toscatranslator.providers.common.all_requirements import ProviderRequirements


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
