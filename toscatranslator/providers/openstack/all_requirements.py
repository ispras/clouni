from toscatranslator.providers.common.all_requirements import ProviderRequirements


class OpenstackRequirements (ProviderRequirements):

    NODE_NAME_BY_REQUIREMENT_NAME = dict(
        boot_volume='volume',
        flavor='flavor',
        image='image',
        interfaces='subnet',
        network='network',
        network_name='network',
        nics=('network', 'port'),
        security_group='security_group',
        security_groups='security_group',
        server='server',
        snapshot_id='volume',
        volumes='volume'
    )

    PROVIDER = 'openstack'
