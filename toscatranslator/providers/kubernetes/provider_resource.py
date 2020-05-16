from toscatranslator.common import snake_case

from toscatranslator.providers.common.provider_resource import ProviderResource


class KubernetesProviderResource(ProviderResource):
    SUPPORTED_CONFIGURATION_TOOLS = [
        "kubernetes"
    ]

    NODE_PRIORITY_BY_TYPE = dict(
        Deployment=0,
        Service=1,
    )

    PROVIDER = 'kubernetes'