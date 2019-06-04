from toscatranslator.providers.amazon.toscaelements.nodes.compute import ToscaComputeNode
from toscatranslator import tosca_type

TOSCA_ELEMENTS = dict(
    Compute=ToscaComputeNode
)


def translate_from_tosca(node, facts):
    (_, _, type_name) = tosca_type.parse(node.type)
    tosca_elem = TOSCA_ELEMENTS.get(type_name)(node.name, node.entity_tpl, facts)

    return tosca_elem.amazon_elements()


def translate_from_amazon(node, facts):
    nodetemplates = dict()
    nodetemplates[node.name] = node.entity_tpl
    return nodetemplates


TRANSLATE_FUNCTION = dict(
    tosca=translate_from_tosca,
    amazon=translate_from_amazon
)
