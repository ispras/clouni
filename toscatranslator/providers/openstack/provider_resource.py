from toscatranslator.common import snake_case

from toscatranslator.providers.common.provider_resource import ProviderResource
from toscatranslator.providers.openstack.all_requirements import OpenstackRequirements


class OpenstackProviderResource(ProviderResource):

    NODE_PRIORITY_BY_TYPE = dict(
        Flavor=0,
        FloatingIp=3,
        Image=0,
        Keypair=0,
        Network=0,
        Port=1,
        Router=2,
        SecurityGroup=0,
        SecurityGroupRule=1,
        Server=2,
        Subnet=1,
        Volume=1
    )

    ANSIBLE_MODULE_PREFIX = 'os_'
    ANSIBLE_DESCRIPTION_PREFIX = 'Create '

    PROVIDER_REQUIREMENTS = OpenstackRequirements

    def ansible_description_by_type(self):
        desc = self.ANSIBLE_DESCRIPTION_PREFIX + self.type_name
        return desc

    def ansible_module_by_type(self):
        module_name = self.ANSIBLE_MODULE_PREFIX + snake_case.convert(self.type_name)
        return module_name
