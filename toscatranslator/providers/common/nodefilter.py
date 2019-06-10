from toscatranslator.providers.combined.combined_facts import FACT_NAME_BY_NODE_NAME, REFACTORING_FACT_KEYS
from toscatranslator.common import tosca_type


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
    def make_fact_value(fact_value, ref_keys, input_fact):
        num_keys = len(ref_keys)
        for i in range(num_keys):
            k = ref_keys[i]
            if fact_value is None:
                fact_value = input_fact.get(k)
            elif isinstance(fact_value, dict):
                fact_value = fact_value if fact_value.get(k) is None else fact_value.get(k)
            elif isinstance(fact_value, list):
                fact_value = [ProviderNodeFilter.make_fact_value(value, ref_keys[i:], input_fact)
                              for value in fact_value]
            else:
                return fact_value
        return fact_value

    @staticmethod
    def refactor_facts(facts, provider, provider_defs):
        """
        Makes facts consistent with provider definition, facts only used for capabilities.properties and properties
        :param provider:
        :param provider_defs:
        :param facts: dictionary contains parameters from ansible facts
        :return: dictionary contains parameters as in provider definition
        """
        refactored_facts = dict()
        fact_name_by_node_name = FACT_NAME_BY_NODE_NAME.get(provider)  # NOTE: ensured is not None
        for def_type, definition in provider_defs.items():  # is a dict, not list
            (_, category, type_name) = tosca_type.parse(def_type)
            if category != 'nodes':
                continue
            fact_name = fact_name_by_node_name.get(type_name.lower())  # NOTE: could be None
            if fact_name is not None:
                input_facts = facts.get(fact_name)
                refactoring_keys = REFACTORING_FACT_KEYS.get(fact_name, {})
                available_fact_keys = set()
                properties = definition.get('properties', {})
                available_fact_keys.update(properties.keys())
                capabilities = definition.get('capabilities', {})
                for cap_def in capabilities.values():
                    cap_type = cap_def.get('type')
                    if cap_type is not None:
                        cap_type_def = provider_defs.get(cap_type, {})
                        available_fact_keys.update(cap_type_def.get('properties', {}).keys())
                requirements = definition.get('requirements', [])
                available_fact_keys.update(next(iter(req.keys())) for req in requirements)

                output_facts = []
                for input_fact in input_facts:
                    output_fact = {}
                    for fact_key in available_fact_keys:
                        fact_value = input_fact.get(fact_key)
                        if fact_value is None:
                            ref_keys = refactoring_keys.get(fact_key, [])
                            fact_value = ProviderNodeFilter.make_fact_value(None, ref_keys, input_fact)
                        if fact_value is not None:
                            output_fact[fact_key] = fact_value
                    output_facts.append(output_fact)
                refactored_facts[fact_name] = output_facts
        return refactored_facts

    def fact_name_by_node_name(self, node_name):
        return FACT_NAME_BY_NODE_NAME.get(self.provider).get(node_name)
