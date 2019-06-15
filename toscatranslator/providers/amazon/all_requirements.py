from toscatranslator.providers.common.all_requirements import ProviderRequirements


class AmazonRequirements(ProviderRequirements):

    NODE_NAME_BY_REQUIREMENT_NAME = dict(
        device_id=('instance', 'elastic_network_interface'),
        image_id='image',
        network='elastic_network_interface',
        security_groups='security_group',
        subnet_id='virtual_private_cloud_subnet',
        vpc_id='virtual_private_cloud'
    )

    PROVIDER = "amazon"
