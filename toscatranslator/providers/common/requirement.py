from toscatranslator.common.tosca_reserved_keys import REQUIREMENT_DEFAULT_PARAMS, RELATIONSHIP, \
    NAME_SUFFIX, ID_SUFFIX, NAME, ID, NODE_FILTER, CAPABILITIES, PROPERTIES, GET_FUNCTIONS, PARAMETERS, SOURCE, \
    VALUE, EXECUTOR

import json, six, copy, sys, logging


class ProviderRequirement (object):

    DEFAULT_REQUIRED_PARAMS = list(REQUIREMENT_DEFAULT_PARAMS)

    def __init__(self, provider, name, key, data, node_filter_key=None):
        self.provider = provider
        self.name = name
        self.key = key
        self.data = data
        self.relationship = self.data.get(RELATIONSHIP)
        self.node_filter_key = node_filter_key
        self.value = None
        self.artifact = None

        self.requires = copy.deepcopy(self.DEFAULT_REQUIRED_PARAMS)
        if self.name[-5:] == NAME_SUFFIX:
            self.requires = [NAME]
        elif self.name[-3:] == ID_SUFFIX:
            self.requires = [ID]
        self.requires.append(self.name)

        self.filter()

    def filter(self):
        """
        Search for required parameters
        :return:
        """
        # NOTE: only node_filter supported
        data = self.data.get(NODE_FILTER)
        if data is None:
            logging.error("The \'%s\' requirement support only \'node_filter\' parameter "
                          "but only \'%s\' is present" % (self.name, self.data))
            sys.exit(1)
        capabilities = data.get(CAPABILITIES, []) # is the list as the requirements
        properties = data.get(PROPERTIES, [])
        if not isinstance(capabilities, list):
            logging.error("The value \'%s\' must be of type list" % (json.dumps(capabilities)))
            sys.exit(1)
        if not isinstance(properties, list):
            logging.error("The value \'%s\' must be of type list" % (json.dumps(properties)))

        raw_params = {}
        for requires in self.requires:
            for prop in properties:
                raw_params.update(prop)
                temp_value = prop.get(requires)
                if temp_value is not None:
                    self.value = temp_value
                    return

            for cap in capabilities:
                for cap_name, cap_val in cap.items():
                    cap_props = cap_val.get(PROPERTIES, [])
                    for prop in cap_props:
                        raw_params.update(prop)
                        temp_value = prop.get(requires)
                        if temp_value is not None:
                            self.value = temp_value
                            return
        if not self.value:
            self.value = {
                PARAMETERS: raw_params,
                SOURCE: {
                    NODE_FILTER: self.key
                },
                EXECUTOR: '',
                VALUE: ID
            }

    def get_value(self):
        if self.value:
            return self.value
        else:
            return self.data

    def if_contain_get_function(self, value):
        """
        Function isn't used
        :param value:
        :return:
        """
        if isinstance(value, six.string_types):
            return False
        if isinstance(value, dict):
            for k, v in value.items():
                if k in GET_FUNCTIONS:
                    return True
                if self.if_contain_get_function(v):
                    return True
            return False
        if isinstance(value, list):
            for v in value:
                if self.if_contain_get_function(v):
                    return True
            return False
        return False