from toscatranslator.configuration_tools.ansible.configuration_tool import AnsibleConfigurationTool
from toscatranslator.configuration_tools.kubernetes.configuration_tool import KubernetesConfigurationTool

CONFIGURATION_TOOLS = dict(
    ansible=AnsibleConfigurationTool,
    kubernetes=KubernetesConfigurationTool
)