import os

from toscaparser.common.exception import ExceptionCollector
from toscaparser.utils.yamlparser import simple_parse as yaml_parse
from toscaparser.tosca_template import ToscaTemplate

from toscatranslator.common.exception import UnspecifiedParameter
from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate

from toscatranslator.common.tosca_reserved_keys import IMPORTS, TOSCA_DEFINITION_FILE
from toscatranslator.common import utils
from toscatranslator.common.configuration import Configuration


def translate(template_file, validate_only, provider, configuration_tool, cluster_name, is_delete=False, a_file=True, extra=None):
    if a_file:
        template_file = os.path.join(os.getcwd(), template_file)
        with open(template_file, 'r') as f:
            template_content = f.read()
    else:
        template_content = template_file
    template = yaml_parse(template_content)

    config = Configuration()
    def_file = config.get_section(config.MAIN_SECTION).get(TOSCA_DEFINITION_FILE)

    default_import_file = os.path.join(utils.get_project_root_path(), def_file)

    if not template.get(IMPORTS):
        template[IMPORTS] = [
            default_import_file
        ]
    else:
        for i in range(len(template[IMPORTS])):
            template[IMPORTS][i] = os.path.abspath(template[IMPORTS][i])
        template[IMPORTS].append(default_import_file)
    tosca_parser_template_object = ToscaTemplate(yaml_dict_tpl=template, a_file=a_file)

    if validate_only:
        msg = 'The input "%(template_file)s" successfully passed validation.' \
              % {'template_file': template_file if a_file else 'template'}
        return msg

    if not provider:
        ExceptionCollector.appendException(UnspecifiedParameter(
            what=('validate-only', 'provider')
        ))

    tosca = ProviderToscaTemplate(tosca_parser_template_object, provider, cluster_name)
    return tosca.to_configuration_dsl(configuration_tool, is_delete, extra=extra)
