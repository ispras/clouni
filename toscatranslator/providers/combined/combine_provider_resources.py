from toscatranslator.providers.openstack.provider_resource import OpenstackProviderResource
from toscatranslator.providers.amazon.provider_resource import AmazonProviderResource


PROVIDER_RESOURCES = dict(
    openstack=OpenstackProviderResource,
    amazon=AmazonProviderResource
)