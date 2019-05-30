import os

from translator.providers.openstack.nodes.flavor import OpenstackFlavorNode
from translator.providers.openstack.nodes.floating_ip import OpenstackFloatingIpNode
from translator.providers.openstack.nodes.image import OpenstackImageNode
from translator.providers.openstack.nodes.keypair import OpenstackKeypairNode
from translator.providers.openstack.nodes.network import OpenstackNetworkNode
from translator.providers.openstack.nodes.port import OpenstackPortNode
from translator.providers.openstack.nodes.router import OpenstackRouterNode
from translator.providers.openstack.nodes.security_group import OpenstackSecurityGroupNode
from translator.providers.openstack.nodes.security_group_rule import OpenstackSecurityGroupRuleNode
from translator.providers.openstack.nodes.server import OpenstackServerNode
from translator.providers.openstack.nodes.subnet import OpenstackSubnetNode
from translator.providers.openstack.nodes.volume import OpenstackVolumeNode

from translator.common.tosca_template import ProviderToscaTemplate


class OpenstackToscaTemplate(ProviderToscaTemplate):

    FILE_DEFINITION = "TOSCA_openstack_definition_1_0.yaml"

    TYPE_NODES = dict(
        Flavor=OpenstackFlavorNode,
        FloatingIp=OpenstackFloatingIpNode,
        Image=OpenstackImageNode,
        Keypair=OpenstackKeypairNode,
        Network=OpenstackNetworkNode,
        Port=OpenstackPortNode,
        Router=OpenstackRouterNode,
        SecurityGroup=OpenstackSecurityGroupNode,
        SecurityGroupRule=OpenstackSecurityGroupRuleNode,
        Server=OpenstackServerNode,
        Subnet=OpenstackSubnetNode,
        Volume=OpenstackVolumeNode
    )

    # NOTE: FACTS have properties of correspond capability
    TYPE_FACTS = {'Flavor', 'Image', 'Network', 'Port', 'Server', 'Subnet'}

    def __init__(self, path=None, parsed_params=None, a_file=True,
                 yaml_dict_tpl=None, yaml_tpl=None, facts=None):

        self.definition_file = os.path.join(os.path.dirname(__file__), self.FILE_DEFINITION)

        super(OpenstackToscaTemplate, self).__init__("openstack", path=path, parsed_params=parsed_params, a_file=a_file,
                                                     yaml_dict_tpl=yaml_dict_tpl, yaml_tpl=yaml_tpl, facts=facts)
