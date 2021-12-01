from toscatranslator.configuration_tools.ansible.configuration_tool import AnsibleConfigurationTool
from toscatranslator.configuration_tools.kubernetes.configuration_tool import KubernetesConfigurationTool

import logging

CONFIGURATION_TOOLS = [
    AnsibleConfigurationTool,
    KubernetesConfigurationTool
]


def get_configuration_tool_class(tool_name):
    possible_values = []
    for tool_class in CONFIGURATION_TOOLS:
        if tool_class.TOOL_NAME == tool_name:
            return tool_class
        possible_values.append(tool_class.TOOL_NAME)
    logging.error("Configuration tool \'%s\' wasn't found. Possible values: \'%s\'" % (tool_name, possible_values))
