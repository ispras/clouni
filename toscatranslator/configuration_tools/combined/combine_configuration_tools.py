from toscatranslator.configuration_tools.ansible.configuration_tool import AnsibleConfigurationTool
from toscatranslator.common.tosca_reserved_keys import ANSIBLE, KUBERNETES
from toscatranslator.configuration_tools.kubernetes.configuration_tool import KubernetesConfigurationTool

CONFIGURATION_TOOLS = {
    ANSIBLE: AnsibleConfigurationTool,
    KUBERNETES: KubernetesConfigurationTool
}
