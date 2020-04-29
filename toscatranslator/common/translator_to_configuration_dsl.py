import json
import os

from toscaparser.common.exception import ExceptionCollector
from toscaparser.utils.yamlparser import simple_parse as yaml_parse
from toscaparser.tosca_template import ToscaTemplate

from toscatranslator.common.exception import UnspecifiedParameter
from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate


def translate(template_file, validate_only, provider, configuration_tool, a_file=True):
    if a_file:
        tosca_parser_template_object = ToscaTemplate(path=template_file, a_file=a_file)
    else:
        template_content = template_file
        template = yaml_parse(template_content)
        tosca_parser_template_object = ToscaTemplate(yaml_dict_tpl=template, a_file=a_file)

    if validate_only:
        msg = 'The input "%(template_file)s" successfully passed validation.' \
              % {'template_file': template_file if a_file else 'template'}
        return msg

    if not provider:
        ExceptionCollector.appendException(UnspecifiedParameter(
            what=('validate-only', 'provider')
        ))

    tosca = ProviderToscaTemplate(tosca_parser_template_object, provider)
    return tosca.to_configuration_dsl_for_create(configuration_tool)
