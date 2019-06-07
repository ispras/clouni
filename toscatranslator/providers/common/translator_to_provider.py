from toscatranslator.common import tosca_type
from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import UnspecifiedProviderTranslatorForNamespaceError

import copy


def translate(translator_funcs, node_templates, facts):
    new_node_templates = {}
    for node in node_templates:
        (namespace, _, _) = tosca_type.parse(node.type)
        translator = translator_funcs.get(namespace)
        if not translator:
            ExceptionCollector.appendException(UnspecifiedProviderTranslatorForNamespaceError(
                what=namespace
            ))
        temp_node_templates = translator(node, facts)  # returns dict_tpl
        for k, v in temp_node_templates.items():
            new_node_templates[k] = copy.deepcopy(v)

    return new_node_templates
