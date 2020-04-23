from toscatranslator.providers.openstack.provider_resource import OpenstackProviderResource
from toscatranslator.providers.amazon.provider_resource import AmazonProviderResource
from toscatranslator.providers.kubernetes.provider_resource import KubernetesProviderResource

PROVIDER_RESOURCES = dict(
    openstack=OpenstackProviderResource,
    amazon=AmazonProviderResource,
    kubernetes=KubernetesProviderResource
)