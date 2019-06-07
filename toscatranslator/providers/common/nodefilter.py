from toscatranslator.providers.combined.combined_facts import FACT_NAME_BY_NODE_NAME


class ProviderNodeFilter(object):

    """
    facts attribute: Class has additional attribute filled in toscatranslator.providers.common.tosca_template
    """
    def __init__(self, provider, key):
        self.provider = provider

        if isinstance(key, tuple):
            self.facts_keys = set(self.fact_name_by_node_name(k) for k in key)
        else:
            self.facts_keys = set()
        self.all_facts = self.facts
        self.facts = []
        for facts_key in self.facts_keys:
            self.facts += self.all_facts.get(facts_key, [])

        # TODO Make dictionary plain, deprecated after refactor
        for i in range(0, len(self.facts)):
            self.facts[i] = dict((str(k), str(v)) for k, v in self.facts[i].items())

    def filter_params(self, params):
        matched_objs = self.facts
        for param, filter_value in params.items():
            filter_str = str(filter_value)
            matched_objs = (obj for obj in matched_objs if filter_str == obj.get(param))

        first_matched = next(iter(matched_objs), {})
        return first_matched

    def filter_node(self, req_data):
        filter_params = req_data.get('properties', {})
        capabilities = req_data.get('capabilities', {})
        for cap_val in capabilities.values():
            filter_params.update(cap_val.get('properties', {}))
        return self.filter_params(filter_params)

    def get_required_value(self, req_data, required_params):
        """
        :param req_data: data of requirement to match
        :param required_params: parameters which are required to be returned
        :return: value of required parameter
        """
        first_matched = self.filter_node(req_data)
        for param in required_params:
            value = first_matched.get(param)
            if value:
                return value
        return None

    @staticmethod
    def refactor_facts(facts):
        """
        Makes facts consistent with provider definition, facts only used for capabilities.properties and properties
        :param facts: dictionary contains parameters from ansible facts
        :return: dictionary contains parameters as in provider definition
        """
        return facts

    def fact_name_by_node_name(self, node_name):
        return FACT_NAME_BY_NODE_NAME.get(self.provider).get(node_name)
