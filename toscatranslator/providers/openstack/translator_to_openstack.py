from toscatranslator.providers.openstack.toscaelements.nodes.compute import ToscaComputeNode
from toscatranslator.common import tosca_type

TOSCA_ELEMENTS = dict(
    Compute=ToscaComputeNode
)


def translate_from_openstack(node, facts):
    nodetemplates = dict()
    nodetemplates[node.name] = node.entity_tpl
    return nodetemplates


def translate_from_tosca(node, facts):
    (_, _, type_name) = tosca_type.parse(node.type)
    tosca_elem = TOSCA_ELEMENTS.get(type_name)(node, facts)

    return tosca_elem.openstack_elements()


TRANSLATE_FUNCTION = dict(
    tosca=translate_from_tosca,
    openstack=translate_from_openstack
)
