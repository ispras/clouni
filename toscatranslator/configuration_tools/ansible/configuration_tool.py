from toscatranslator.configuration_tools.common.configuration_tool import ConfigurationTool
import copy
import yaml

from random import randint,seed
from time import time


class AnsibleConfigurationTool(ConfigurationTool):
    """
    Must be tested by TestAnsibleOpenstack.test_translating_to_ansible
    """

    def to_dsl_for_create(self, provider, nodes_queue):
        ansible_task_list = []
        for node in nodes_queue:
            ansible_task_list.append(self.get_ansible_task_for_create(node))
        ansible_playbook = [dict(
            name='Create ' + provider + ' cluster',
            hosts='all',
            tasks=ansible_task_list
        )]
        return ansible_playbook

    def get_ansible_task_for_create(self, node, additional_args=None):
        """
        Fulfill the dict with ansible task arguments to create infrastructure
        If the node contains get_operation_output parameters then the operation is executed
        If the operation is not mentioned then it is not executed
        Operations are mentioned in the node or in relationship_template
        :param: node: ProviderResource
        :param additional_args: dict of arguments to add
        :return: string of ansible task to place in playbook
        """

        # seed(time())
        # id = randint(1000, 9999)

        if additional_args is None:
            additional_args = {}
        try:
            ansible_args = copy.copy(node.configuration_args)
            ansible_args['state'] = 'present'
            ansible_args.update(additional_args)
            self.ansible_task_as_dict = dict()
            self.ansible_task_as_dict['name'] = node.ansible_description_by_type()
            self.ansible_task_as_dict[node.ansible_module_by_type()] = node.configuration_args
            self.ansible_task = yaml.dump(self.ansible_task_as_dict)
        except AttributeError:
            pass

        return self.ansible_task_as_dict
