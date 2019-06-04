from toscatranslator import tosca_type
from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import UnspecifiedTranslatorForProviderError, \
    UnspecifiedProviderTranslatorForNamespaceError
from toscatranslator.providers.combined.combine_translators import TRANSLATE_FUNCTION

from toscaparser.topology_template import TopologyTemplate

import copy


def translate(provider, tosca_topology_template, facts, custom_defs):
    dict_tpl = copy.deepcopy(tosca_topology_template.tpl)
    translator_funcs = TRANSLATE_FUNCTION.get(provider)
    if not translator_funcs:
        ExceptionCollector.appendException(UnspecifiedTranslatorForProviderError(
            what=provider
        ))

    new_node_templates = {}
    nodetemplates = tosca_topology_template.nodetemplates
    for node in nodetemplates:
        (namespace, _, _) = tosca_type.parse(node.type)
        translator = translator_funcs.get(namespace)
        if not translator:
            ExceptionCollector.appendException(UnspecifiedProviderTranslatorForNamespaceError(
                what=namespace
            ))
        temp_node_templates = translator(node, facts)  # returns dict_tpl
        for k, v in temp_node_templates.items():
            new_node_templates[k] = copy.deepcopy(v)

    for k, v in new_node_templates.items():
        dict_tpl['node_templates'][k] = v

    rel_types = []
    for k, v in custom_defs.items():
        (_, element_type, _) = tosca_type.parse(k)
        if element_type == 'relationship_types':
            rel_types.append(v)
    topology_tpl = TopologyTemplate(dict_tpl, custom_defs, rel_types)

    return topology_tpl
