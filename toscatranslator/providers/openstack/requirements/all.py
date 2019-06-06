from toscatranslator.providers.openstack.requirements.flavor import OpenstackFlavorRequirement
from toscatranslator.providers.openstack.requirements.image import OpenstackImageRequirement
from toscatranslator.providers.openstack.requirements.network import OpenstackNetworkRequirement
from toscatranslator.providers.openstack.requirements.security_group import OpenstackSecurityGroupRequirement
from toscatranslator.providers.openstack.requirements.server import OpenstackServerRequirement
from toscatranslator.providers.openstack.requirements.subnet import OpenstackSubnetRequirement
from toscatranslator.providers.openstack.requirements.volume import OpenstackVolumeRequirement

from toscatranslator.providers.openstack.nodefilters.flavor import OpenstackFlavorNodeFilter
from toscatranslator.providers.openstack.nodefilters.image import OpenstackImageNodeFilter
from toscatranslator.providers.openstack.nodefilters.network import OpenstackNetworkNodeFilter
from toscatranslator.providers.openstack.nodefilters.port import OpenstackPortNodeFilter
from toscatranslator.providers.openstack.nodefilters.server import OpenstackServerNodeFilter
from toscatranslator.providers.openstack.nodefilters.subnet import OpenstackSubnetNodeFilter

from toscatranslator.providers.common.all_requirements import ProviderRequirements


class OpenstackRequirements (ProviderRequirements):

    FLAVOR = OpenstackFlavorRequirement
    IMAGE = OpenstackImageRequirement
    NETWORK = OpenstackNetworkRequirement
    SECURITY_GROUP = OpenstackSecurityGroupRequirement
    SERVER = OpenstackServerRequirement
    SUBNET = OpenstackSubnetRequirement
    VOLUME = OpenstackVolumeRequirement

    REQUIREMENT_KEY_BY_NAME = dict(
        boot_volume='volume',
        flavor='flavor',
        image='image',
        interfaces='subnet',
        network='network',
        network_name='network',
        nics='network',
        security_group='security_group',
        security_groups='security_group',
        server='server',
        snapshot_id='volume',
        volumes='volume'
    )

    REQUIREMENT_CLASS_BY_KEY = dict(
        flavor=FLAVOR,
        image=IMAGE,
        network=NETWORK,
        security_group=SECURITY_GROUP,
        server=SERVER,
        subnet=SUBNET,
        volume=VOLUME
    )

    NODEFILTER_CLASS_BY_KEY = dict(
        flavor=OpenstackFlavorNodeFilter,
        image=OpenstackImageNodeFilter,
        network=OpenstackNetworkNodeFilter,
        port=OpenstackPortNodeFilter,
        server=OpenstackServerNodeFilter,
        subnet=OpenstackSubnetNodeFilter
    )


