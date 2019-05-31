from toscaparser.common.exception import ExceptionCollector

from toscatranslator.common.exception import UnsupportedRequirementError


class ProviderRequirements (object):

    def get_requirements(self, node, possible_requirements):
        requirements = dict()
        # TODO: look through "occurrences" keyword semantic (using a dict consisting of one element look crazy)
        for req in node.requirements:
            req_name = next(iter(req.keys()))
            req_class = self.get.get(req_name)
            if not req_class:
                ExceptionCollector.appendException(UnsupportedRequirementError(
                    what=req_name
                ))
            if req_name in possible_requirements:
                requirement = req_class(req[req_name])
                if req_name in self.REQUIREMENTS_OF_TYPE_LIST:
                    if requirements.get(req_name):
                        requirements[req_name].append(requirement)
                    else:
                        requirements[req_name] = [requirement]
                # ignore unknown parameters
                else:
                    requirements[req_name] = requirement
            elif req_name == 'dependency':
                raise NotImplementedError
        return requirements
