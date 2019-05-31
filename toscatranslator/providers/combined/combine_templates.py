from toscatranslator.providers.openstack.tosca_template import OpenstackToscaTemplate
from toscatranslator.providers.amazon.tosca_template import AmazonToscaTemplate

PROVIDER_TEMPLATES = dict(
    openstack=OpenstackToscaTemplate,
    amazon=AmazonToscaTemplate
)
