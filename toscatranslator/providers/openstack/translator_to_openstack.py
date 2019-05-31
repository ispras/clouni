from toscatranslator.providers.openstack.toscaelements.nodes.compute import ToscaComputeNode
from toscatranslator import tosca_type

TOSCA_ELEMENTS = dict(
    Compute=ToscaComputeNode
)


def translate_from_openstack(node_name, node_template, facts):
    nodetemplates = dict()
    nodetemplates[node_name] = node_template
    return nodetemplates


def translate_from_tosca(node_name, node_template, facts):
    (_, _, type_name) = tosca_type.parse(node_template['type'])
    tosca_elem = TOSCA_ELEMENTS.get(type_name)(node_name, node_template, facts)

    return tosca_elem.openstack_elements()


TRANSLATE_FUNCTION = dict(
    tosca=translate_from_tosca,
    openstack=translate_from_openstack
)
