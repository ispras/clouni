import os

from toscatranslator.providers.openstack.provider_resource import OpenstackProviderResource

from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate
from toscatranslator.providers.openstack.translator_to_openstack import TRANSLATE_FUNCTION


class OpenstackToscaTemplate(ProviderToscaTemplate):

    FILE_DEFINITION = "TOSCA_openstack_definition_1_0.yaml"

    PROVIDER = 'openstack'

    def provider_resource_class(self, node):
        return OpenstackProviderResource(node)

    def translate_functions(self):
        return TRANSLATE_FUNCTION
