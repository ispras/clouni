from toscaparser.common.exception import ExceptionCollector

from toscatranslator.common.exception import UnsupportedRequirementError
from toscatranslator.providers.common.requirement import ProviderRequirement


class ProviderRequirements (object):

    SECTIONS = (OCCURRENCES) = \
        'occurrences'

    def __init__(self, requirement_definitions):
        """
        Get the requirements of type list from requirement definitions
        :param requirement_definitions: list of requirement definitions with name added
        """
        self.requirement_definitions = requirement_definitions
        self.requirement_names_of_type_list = set()
        self.required_requirement_keys = set()
        for req_def in self.requirement_definitions:
            occurrences = req_def.get(self.OCCURRENCES)  # list
            min_ocs = occurrences[0]
            max_ocs = occurrences[1]
            if int(min_ocs) > 0:
                self.required_requirement_keys.add(req_def['name'])
            if str(max_ocs) == 'UNBOUNDED':
                self.requirement_names_of_type_list.add(req_def['name'])
            elif int(max_ocs) > 1:
                self.requirement_names_of_type_list.add(req_def['name'])

    def get_requirements(self, node):
        """
        Initializes requirement objects
        :param node: class NodeTemplate from toscaparser
        :return: list of objects ProviderRequirement
        """
        requirements = dict()
        for req in node.requirements:
            req_name = next(iter(req.keys()))
            req_key = self.node_name_by_requirement_name(req_name)
            if not req_key:
                ExceptionCollector.appendException(UnsupportedRequirementError(
                    what=req_name
                ))
            requirement = ProviderRequirement(self.provider(), req_name, req_key, req[req_name], req_key)
            if req_name in self.requirement_names_of_type_list:
                if requirements.get(req_name) is not None:
                    requirements[req_name].append(requirement)
                else:
                    requirements[req_name] = [requirement]
            # ignore unknown parameters
            else:
                requirements[req_name] = requirement
        return requirements

    def node_name_by_requirement_name(self, name):
        assert self.NODE_NAME_BY_REQUIREMENT_NAME is not None
        return self.NODE_NAME_BY_REQUIREMENT_NAME.get(name)

    def provider(self):
        assert self.PROVIDER is not None
        return self.PROVIDER
