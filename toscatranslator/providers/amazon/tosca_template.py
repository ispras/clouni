import os

from toscatranslator.providers.amazon.nodes.elastic_ip import AmazonElasticIPNode
from toscatranslator.providers.amazon.nodes.elastic_network_interface import AmazonElasticNetworkInterfaceNode
from toscatranslator.providers.amazon.nodes.image import AmazonImageNode
from toscatranslator.providers.amazon.nodes.instance import AmazonInstanceNode
from toscatranslator.providers.amazon.nodes.securty_group import AmazonSecurityGroupNode
from toscatranslator.providers.amazon.nodes.virtual_private_cloud import AmazonVirtualPrivateCloudNode
from toscatranslator.providers.amazon.nodes.virtual_private_cloud_subnet import AmazonVirtualPrivateCloudSubnetNode

from toscatranslator.common.tosca_template import ProviderToscaTemplate


class AmazonToscaTemplate(ProviderToscaTemplate):
    FILE_DEFINITION = "TOSCA_amazon_definition_1_0.yaml"

    TYPE_NODES = dict(
        ElasticIP=AmazonElasticIPNode,
        ElasticNetworkInterface=AmazonElasticNetworkInterfaceNode,
        Image=AmazonImageNode,
        Instance=AmazonInstanceNode,
        SecurityGroup=AmazonSecurityGroupNode,
        VirtualPrivateCloud=AmazonVirtualPrivateCloudNode,
        VirtualPrivateCloudSubnet=AmazonVirtualPrivateCloudSubnetNode
    )

    TYPE_FACTS = {'ElasticNetworkInterface', 'Image', 'VirtualPrivateCloud', 'VirtualPrivateCloudSubnet'}

    def __init__(self, path=None, parsed_params=None, a_file=True,
                 yaml_dict_tpl=None, yaml_tpl=None, facts=None):

        self.definition_file = os.path.join(os.path.dirname(__file__), self.FILE_DEFINITION)

        super(AmazonToscaTemplate, self).__init__("amazon", path=path, parsed_params=parsed_params, a_file=a_file,
                                                  yaml_dict_tpl=yaml_dict_tpl, yaml_tpl=yaml_tpl, facts=facts)
