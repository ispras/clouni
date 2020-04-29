from toscaparser.common.exception import ExceptionCollector

from toscatranslator.common.exception import UnsupportedRequirementError
from toscatranslator.providers.common.requirement import ProviderRequirement

from toscatranslator.common import tosca_type, snake_case
from toscatranslator.providers.common.tosca_reserved_keys import OCCURRENCES, NODE, NAME


class ProviderRequirements (object):

    def __init__(self, requirement_definitions, provider):
        """
        Get the requirements of type list from requirement definitions
        :param requirement_definitions: list of requirement definitions with name added
        """
        self.provider = provider
        self.requirement_definitions = requirement_definitions
        self.requirement_names_of_type_list = set()
        self.node_name_by_requirement_name = dict()

        # NOTE generate the dictionary, where the keys are the name of requirement and
        # the values are the node_types of requirement
        for req_def in self.requirement_definitions:
            req_name = req_def[NAME]
            req_node = req_def.get(NODE)
            if req_node:
                (_, _, type_name) = tosca_type.parse(req_node)
                node_name = snake_case.convert(type_name)
                if node_name == 'root':
                    continue
                temp_req_val = self.node_name_by_requirement_name.get(req_name)
                if temp_req_val is None:
                    temp_req_val = node_name
                elif isinstance(temp_req_val, str):
                    temp_req_val = (temp_req_val, node_name)
                else:
                    temp_req_val = temp_req_val + (node_name)
                self.node_name_by_requirement_name[req_name] = temp_req_val

        # NOTE set the list required requirements and the list of multiple requirements (of type list)
        self.required_requirement_keys = set()
        for req_def in self.requirement_definitions:
            occurrences = req_def.get(OCCURRENCES)  # list
            min_ocs = occurrences[0]
            max_ocs = occurrences[1]
            if int(min_ocs) > 0:
                self.required_requirement_keys.add(req_def[NAME])
            if str(max_ocs) == 'UNBOUNDED':
                self.requirement_names_of_type_list.add(req_def[NAME])
            elif int(max_ocs) > 1:
                self.requirement_names_of_type_list.add(req_def[NAME])

    def get_requirements(self, node):
        """
        Initializes requirement objects
        :param node: class NodeTemplate from toscaparser
        :return: list of objects ProviderRequirement
        """
        requirements = dict()
        for req in node.requirements:
            req_name = next(iter(req.keys()))
            req_key = self.node_name_by_requirement_name.get(req_name)
            if not req_key:
                ExceptionCollector.appendException(UnsupportedRequirementError(
                    what=req_name
                ))
            requirement = ProviderRequirement(self.provider, req_name, req_key, req[req_name], req_key)
            if req_name in self.requirement_names_of_type_list:
                if requirements.get(req_name) is not None:
                    requirements[req_name].append(requirement)
                else:
                    requirements[req_name] = [requirement]
            # ignore unknown parameters
            else:
                requirements[req_name] = requirement
        return requirements
