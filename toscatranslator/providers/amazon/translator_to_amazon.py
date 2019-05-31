from toscatranslator.providers.amazon.toscaelements.nodes.compute import ToscaComputeNode
from toscatranslator import tosca_type

TOSCA_ELEMENTS = dict(
    Compute=ToscaComputeNode
)


def translate_from_tosca(node_name, node_template, facts):
    (_, _, type_name) = tosca_type.parse(node_template['type'])
    tosca_elem = TOSCA_ELEMENTS.get(type_name)(node_name, node_template, facts)

    return tosca_elem.amazon_elements()


def translate_from_amazon(node_name, node_template, facts):
    nodetemplates = dict()
    nodetemplates[node_name] = node_template
    return nodetemplates


TRANSLATE_FUNCTION = dict(
    tosca=translate_from_tosca,
    amazon=translate_from_amazon
)
