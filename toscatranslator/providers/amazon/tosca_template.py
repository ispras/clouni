from toscatranslator.providers.amazon.provider_resource import AmazonProviderResource
from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate


class AmazonToscaTemplate(ProviderToscaTemplate):
    FILE_DEFINITION = "TOSCA_amazon_definition_1_0.yaml"
    TOSCA_ELEMENTS_MAP_FILE = "tosca_elements_map_to_amazon.json"

    PROVIDER = 'amazon'

    def provider_resource_class(self, node):
        return AmazonProviderResource(node)
