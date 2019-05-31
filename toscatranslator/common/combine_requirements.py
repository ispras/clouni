from toscatranslator.providers.openstack.requirements.all import OpenstackRequirements
from toscatranslator.providers.amazon.requirements.all import AmazonRequirements

PROVIDER_REQUIREMENTS = dict(
    openstack=OpenstackRequirements,
    amazon=AmazonRequirements
)
