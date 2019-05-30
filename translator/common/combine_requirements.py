from translator.providers.openstack.requirements.all import OpenstackRequirements
from translator.providers.amazon.requirements.all import AmazonRequirements

PROVIDER_REQUIREMENTS = dict(
    openstack=OpenstackRequirements,
    amazon=AmazonRequirements
)
