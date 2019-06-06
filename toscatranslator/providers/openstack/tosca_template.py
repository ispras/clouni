import os

from toscatranslator.providers.openstack.nodes.flavor import OpenstackFlavorNode
from toscatranslator.providers.openstack.nodes.floating_ip import OpenstackFloatingIpNode
from toscatranslator.providers.openstack.nodes.image import OpenstackImageNode
from toscatranslator.providers.openstack.nodes.keypair import OpenstackKeypairNode
from toscatranslator.providers.openstack.nodes.network import OpenstackNetworkNode
from toscatranslator.providers.openstack.nodes.port import OpenstackPortNode
from toscatranslator.providers.openstack.nodes.router import OpenstackRouterNode
from toscatranslator.providers.openstack.nodes.security_group import OpenstackSecurityGroupNode
from toscatranslator.providers.openstack.nodes.security_group_rule import OpenstackSecurityGroupRuleNode
from toscatranslator.providers.openstack.nodes.server import OpenstackServerNode
from toscatranslator.providers.openstack.nodes.subnet import OpenstackSubnetNode
from toscatranslator.providers.openstack.nodes.volume import OpenstackVolumeNode

from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate


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

    PROVIDER = 'openstack'

    def __init__(self, tosca_parser_template_object, facts):

        self.definition_file = os.path.join(os.path.dirname(__file__), self.FILE_DEFINITION)

        super(OpenstackToscaTemplate, self).__init__(tosca_parser_template_object, facts)
