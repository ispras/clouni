from toscatranslator.providers.amazon.provider_resource import AmazonProviderResource
from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate


class AmazonToscaTemplate(ProviderToscaTemplate):
    FILE_DEFINITION = "TOSCA_amazon_definition_1_0.yaml"

    PROVIDER = 'amazon'

    def provider_resource_class(self, node):
        return AmazonProviderResource(node)
