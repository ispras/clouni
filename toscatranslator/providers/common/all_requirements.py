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
            req_key = self.requirement_key_by_name(req_name)
            if not req_key:
                ExceptionCollector.appendException(UnsupportedRequirementError(
                    what=req_name
                ))
            node_filter_key = self.nodefilter_key_by_key(req_key)
            requirement = ProviderRequirement(self.provider(), req_name, req_key, req[req_name], node_filter_key)
            if req_name in self.requirement_names_of_type_list:
                if requirements.get(req_name) is not None:
                    requirements[req_name].append(requirement)
                else:
                    requirements[req_name] = [requirement]
            # ignore unknown parameters
            else:
                requirements[req_name] = requirement
        return requirements

    def requirement_key_by_name(self, name):
        raise NotImplementedError()

    def nodefilter_key_by_key(self, key):
        raise NotImplementedError()

    def provider(self):
        raise NotImplementedError()
