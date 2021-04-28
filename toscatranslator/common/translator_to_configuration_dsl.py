import os

from toscaparser.common.exception import ExceptionCollector
from toscaparser.utils.yamlparser import simple_parse as yaml_parse
from toscaparser.tosca_template import ToscaTemplate

from toscatranslator.common.exception import UnspecifiedParameter, ProviderConfigurationParameterError, \
    UnsupportedExecutorType
from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate

from toscatranslator.common.tosca_reserved_keys import IMPORTS, TOSCA_DEFINITION_FILE, DEFAULT_ARTIFACTS_DIRECTORY,\
    EXECUTOR, NAME
from toscatranslator.common import utils
from toscatranslator.common.configuration import Configuration
from toscatranslator.configuration_tools.combined.combine_configuration_tools import get_configuration_tool_class


REQUIRED_CONFIGURATION_PARAMS = (TOSCA_DEFINITION_FILE, DEFAULT_ARTIFACTS_DIRECTORY)


def translate(template_file, validate_only, provider, configuration_tool, cluster_name, is_delete=False, a_file=True,
              extra=None):
    """
    Main function, is called by different shells, i.e. bash, Ansible module, grpc
    :param template_file: filename of TOSCA template or TOSCA template data if a_file is False
    :param validate_only: boolean, if template should be only validated
    :param provider: key of cloud provider
    :param configuration_tool: key of configuration tool
    :param cluster_name: name to point to desired infrastructure as one component
    :param is_delete: generate dsl scripts for infrastructure deletion
    :param a_file: if template_file is filename
    :param extra: extra for template
    :return: string that is a script to deploy or delete infrastructure
    """

    config = Configuration()
    for sec in REQUIRED_CONFIGURATION_PARAMS:
        if sec not in config.get_section(config.MAIN_SECTION).keys():
            raise ProviderConfigurationParameterError(
                what=sec
            )

    if a_file:
        template_file = os.path.join(os.getcwd(), template_file)
        with open(template_file, 'r') as f:
            template_content = f.read()
    else:
        template_content = template_file
    template = yaml_parse(template_content)

    def_file = config.get_section(config.MAIN_SECTION).get(TOSCA_DEFINITION_FILE)

    default_import_file = os.path.join(utils.get_project_root_path(), def_file)

    # Add default import of normative TOSCA types to the template
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

    # Parse and generate new TOSCA service template with only provider specific TOSCA types from normative types
    tosca = ProviderToscaTemplate(tosca_parser_template_object, provider, cluster_name)

    # Init configuration tool class
    tool = get_configuration_tool_class(configuration_tool)()

    default_artifacts_directory = config.get_section(config.MAIN_SECTION).get(DEFAULT_ARTIFACTS_DIRECTORY)

    # Copy used conditions from intermediate service template
    if tosca.used_conditions_set:
        tool.copy_conditions_to_the_directory(tosca.used_conditions_set, default_artifacts_directory)

    # Manage new artifacts for intermediate template
    tool_artifacts = []
    for art in tosca.artifacts:
        executor = art.get(EXECUTOR)
        if bool(executor) and executor != configuration_tool:
            art_list = [ art ]
            new_arts = generate_artifacts(art_list, default_artifacts_directory)
            tosca.artifacts.extend(new_arts)
        else:
            tool_artifacts.append(art)

    if not extra:
        extra = {}
    extra_full = utils.deep_update_dict(extra, tosca.extra_configuration_tool_params.get(configuration_tool, {}))

    configuration_content = tool.to_dsl_for_create(tosca.provider, tosca.provider_nodes_queue, tool_artifacts,
                                                   default_artifacts_directory, tosca.cluster_name, extra=extra_full) \
        if not is_delete else tool.to_dsl_for_delete(tosca.provider, tosca.provider_nodes_queue, tosca.cluster_name,
                                                     extra=extra_full)
    return configuration_content


def generate_artifacts(new_artifacts, directory):
    """
    From the info of new artifacts generate files which execute
    :param new_artifacts: list of dicts containing (value, source, parameters, executor, name, configuration_tool)
    :return: None
    """
    r_artifacts = []
    for art in new_artifacts:
        filename = os.path.join(directory, art[NAME])
        configuration_class = get_configuration_tool_class(art[EXECUTOR])()
        if not configuration_class:
            ExceptionCollector.appendException(UnsupportedExecutorType(
                what=art[EXECUTOR]
            ))
        configuration_class.create_artifact(filename, art)
        r_artifacts.append(filename)

    return r_artifacts
