from toscatranslator.configuration_tools.ansible.configuration_tool import AnsibleConfigurationTool
from toscatranslator.configuration_tools.kubernetes.configuration_tool import KubernetesConfigurationTool

CONFIGURATION_TOOLS = [
    AnsibleConfigurationTool,
    KubernetesConfigurationTool
]


def get_configuration_tool_class(tool_name):
    for tool_class in CONFIGURATION_TOOLS:
        if tool_class.TOOL_NAME == tool_name:
            return tool_class
