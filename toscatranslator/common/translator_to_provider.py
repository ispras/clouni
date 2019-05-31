from toscatranslator import tosca_type
from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import UnspecifiedTranslatorForProviderError, \
    UnspecifiedProviderTranslatorForNamespaceError
from toscatranslator.common.combine_translators import TRANSLATE_FUNCTION


def translate(provider, dict_tpl, facts, definition_file):
    translator_funcs = TRANSLATE_FUNCTION.get(provider)
    if not translator_funcs:
        ExceptionCollector.appendException(UnspecifiedTranslatorForProviderError(
            what=provider
        ))
    new_node_templates = {}
    nodetemplates = dict_tpl.get('topology_template', {}).get('node_templates', {})
    for node_name, node in nodetemplates.items():
        (namespace, _, _) = tosca_type.parse(node['type'])
        translator = translator_funcs.get(namespace)
        if not translator:
            ExceptionCollector.appendException(UnspecifiedProviderTranslatorForNamespaceError(
                what=namespace
            ))
        temp_node_templates = translator(node_name, node, facts)
        for k, v in temp_node_templates.items():
            new_node_templates[k] = v

    for k, v in new_node_templates.items():
        dict_tpl['topology_template']['node_templates'][k] = v
    if not dict_tpl.get('imports'):
        dict_tpl['imports'] = [definition_file]
    else:
        dict_tpl['imports'].append(definition_file)

    return dict_tpl
