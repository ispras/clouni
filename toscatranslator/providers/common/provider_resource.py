import yaml
from toscatranslator.providers.combined.combine_requirements import PROVIDER_REQUIREMENTS


class ProviderResource(object):

    MAX_NUM_PRIORITIES = 5
    CAPABILITY_NAME = 'self'

    def __init__(self, node):
        """

        :param node: NodeTemplate class
        """
        assert self.PRIORITY is not None
        assert self.ANSIBLE_DESCRIPTION is not None
        assert self.ANSIBLE_MODULE is not None
        assert self.PROVIDER

        self.pb = ''
        # NOTE: filling the parameters from openstack definition to parse from input template
        type_definition = node.type_definition  # toscaparser.elements.nodetype.NodeType
        self.possible_requirements = set(next(iter(req.keys())) for req in type_definition.defs.get('requirements', {}))

        self_capability = type_definition.defs.get('capabilities', {}).get(self.CAPABILITY_NAME)
        if self_capability:
            self.capability_type = \
                self_capability.get('type')
            self.capability_properties = \
                set(type_definition.custom_def.get(self.capability_type, {}).get('properties', {}).keys())

        self.property_params = set(type_definition.defs.get('properties', {}).keys())
        self.artifacts = set(type_definition.defs.get('artifacts', {}).keys())

        # Get the parameters from template using openstack definition
        self.ansible_params = dict()
        if type(node) is dict:
            raise Exception("Ya vot seychas")
            # # NOTE: parameters came not from ToscaTemplate but as dict
            # properties = node.get('properties', {})
            # for key, value in properties.items():
            #     if key in self.property_params:
            #         self.ansible_params[key] = value
            #
            # if self.CAPABILITY_NAME:
            #     properties = node.get('capabilities', {}).get(self.CAPABILITY_NAME, {}).get('properties', {})
            #     for key, val in properties.items():
            #         if key in self.capability_properties:
            #             self.ansible_params[key] = val
            #
            # artifacts = node.get('artifacts', {})
            # for key, val in artifacts.items():
            #     if key in self.artifacts:
            #         self.ansible_params[key] = value
        else:
            # NOTE: node is NodeTemplate instance
            for key in self.property_params:
                value = node.get_property_value(key)
                if value is not None:
                    self.ansible_params[key] = value

            if self.CAPABILITY_NAME:
                # NOTE: properties is Property class TODO: type class
                properties = node.get_capabilities().get(self.CAPABILITY_NAME)
                if properties:
                    for key in self.capability_properties:
                        value = properties.get_property_value(key)
                        if value:
                            self.ansible_params[key] = value

            if hasattr(node, 'artifacts'):
                # TODO: oneliner
                for key, value in node.artifacts:
                    self.ansible_params[key] = value

            self.requirements = PROVIDER_REQUIREMENTS[self.PROVIDER]().get_requirements(node, self.possible_requirements)
            for key, req in self.requirements.items():
                if type(req) is list:
                    self.ansible_params[key] = list(v.to_ansible() for v in req)
                else:
                    self.ansible_params[key] = req.to_ansible()

    def to_ansible(self):
        self.ansible_params['state'] = 'present'
        pb_dict = dict()
        pb_dict['name'] = self.ANSIBLE_DESCRIPTION
        pb_dict[self.ANSIBLE_MODULE] = self.ansible_params
        self.pb = yaml.dump(pb_dict)

        raise NotImplementedError

    def get_ansible_params(self):
        return self.ansible_params
