import json
import os

from toscaparser.common.exception import ExceptionCollector
from toscaparser.utils.yamlparser import simple_parse as yaml_parse
from toscaparser.tosca_template import ToscaTemplate

from toscatranslator.common.exception import UnknownProvider, UnsupportedFactsFormat, UnspecifiedParameter
from toscatranslator.providers.combined.combine_templates import PROVIDER_TEMPLATES


def translate(template_file, validate_only, provider, _facts, a_file=True):
    if a_file:
        tosca_parser_template_object = ToscaTemplate(path=template_file, a_file=a_file)
    else:
        template_content = template_file
        template = yaml_parse(template_content)
        tosca_parser_template_object = ToscaTemplate(yaml_dict_tpl=template, a_file=a_file)

    facts = dict()
    if _facts is not None:
        if type(_facts) is dict:
            facts = _facts
        elif os.path.isfile(_facts):
            with open(_facts, "r") as ff:
                facts = json.load(ff)
        else:
            raise UnsupportedFactsFormat()

    if validate_only:
        msg = 'The input "%(template_file)s" successfully passed validation.' \
              % {'template_file': template_file if a_file else 'template'}
        return msg

    if not provider:
        ExceptionCollector.appendException(UnspecifiedParameter(
            what=('validate-only', 'provider')
        ))

    tosca_template_class = PROVIDER_TEMPLATES.get(provider)
    if not tosca_template_class:
        ExceptionCollector.appendException(UnknownProvider(
            what=provider
        ))
    tosca = tosca_template_class(tosca_parser_template_object, facts)
    return tosca.to_ansible_role_for_create()
