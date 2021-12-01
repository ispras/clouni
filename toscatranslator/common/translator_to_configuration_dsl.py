import six
from toscaparser.tosca_template import ToscaTemplate

from toscatranslator.providers.common.tosca_template import ProviderToscaTemplate
from toscatranslator.common.tosca_reserved_keys import IMPORTS, TOSCA_DEFINITION_FILE, DEFAULT_ARTIFACTS_DIRECTORY,\
    EXECUTOR, NAME
from toscatranslator.common import utils
from toscatranslator.common.configuration import Configuration
from toscatranslator.configuration_tools.combined.combine_configuration_tools import get_configuration_tool_class


import logging
import json, os, sys, yaml


REQUIRED_CONFIGURATION_PARAMS = (TOSCA_DEFINITION_FILE, DEFAULT_ARTIFACTS_DIRECTORY)


def translate(template_file, validate_only, provider, configuration_tool, cluster_name, is_delete=False, a_file=True,
              extra=None, log_level='info'):
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
    log_map = dict(
        debug=logging.DEBUG,
        info=logging.INFO,
        warning=logging.WARNING,
        error=logging.ERROR,
        critical=logging.ERROR
    )

    logging_format = "%(asctime)s %(levelname)s %(message)s"
    logging.basicConfig(filename=os.path.join(os.getenv('HOME'), '.clouni.log'), filemode='a', level=log_map[log_level],
                        format=logging_format, datefmt='%Y-%m-%d %H:%M:%S')
    logging.info("Started translation of TOSCA template \'%s\' for provider \'%s\' and configuration tool \'%s\'" %
                 (template_file if a_file else 'raw', provider, configuration_tool))
    logging.info("Cluster name set to \'%s\'" % cluster_name)
    logging.info("Deploying script for cluster %s will be created" % 'deletion' if is_delete else 'creation')
    logging.info("Extra parameters to the unit of deployment scripts will be added: %s" % json.dumps(extra))
    logging.info("Log level is set to %s" % log_level)

    config = Configuration()
    for sec in REQUIRED_CONFIGURATION_PARAMS:
        if sec not in config.get_section(config.MAIN_SECTION).keys():
            logging.error('Provider configuration parameter "%s" is missing in configuration file' % sec)
            sys.exit(1)

    if a_file:
        template_file = os.path.join(os.getcwd(), template_file)
        with open(template_file, 'r') as f:
            template_content = f.read()
    else:
        template_content = template_file

    try:
        template = yaml.load(template_content, Loader=yaml.SafeLoader)
    except yaml.scanner.ScannerError as e:
        logging.error("Error parsing TOSCA template: %s%s" % (e.problem, e.context_mark))
        sys.exit(1)

    def_files = config.get_section(config.MAIN_SECTION).get(TOSCA_DEFINITION_FILE)
    if isinstance(def_files, six.string_types):
        def_files = [ def_files ]
    default_import_files = []
    for def_file in def_files:
        default_import_files.append(os.path.join(utils.get_project_root_path(), def_file))
    logging.info("Default TOSCA template definition file to be imported \'%s\'" % json.dumps(default_import_files))

    # Add default import of normative TOSCA types to the template
    if not template.get(IMPORTS):
        template[IMPORTS] = []
    for i in range(len(template[IMPORTS])):
        template[IMPORTS][i] = os.path.abspath(template[IMPORTS][i])
    template[IMPORTS].extend(default_import_files)

    try:
        tosca_parser_template_object = ToscaTemplate(yaml_dict_tpl=template, a_file=a_file)
    except:
        logging.exception("Got exception from OpenStack tosca-parser")
        sys.exit(1)

    if validate_only:
        msg = 'The input "%(template_file)s" successfully passed validation.' \
              % {'template_file': template_file if a_file else 'TOSCA template'}
        return msg

    if not provider:
        logging.error("Provider must be specified unless \'validate-only\' flag is used")
        sys.exit(1)

    # Parse and generate new TOSCA service template with only provider specific TOSCA types from normative types
    tosca = ProviderToscaTemplate(tosca_parser_template_object, provider, cluster_name, debug)

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

    configuration_content = tool.to_dsl(tosca.provider, tosca.provider_nodes_queue, tosca.cluster_name, is_delete,
                                        tool_artifacts, default_artifacts_directory,
                                        inputs=tosca.inputs, outputs=tosca.outputs, extra=extra_full)

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
            sys.exit(1)
        configuration_class.create_artifact(filename, art)
        r_artifacts.append(filename)

    return r_artifacts
