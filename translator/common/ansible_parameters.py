from translator.common.combine_ansible_parameters import FACTS_BY_PROVIDER, AUTH_PARAM_FUNCS_BY_PROVIDER, FACTS_MODULE_PARAMS_MAP_BY_PROVIDER
from translator.common.exception import UnspecifiedFactsParserForProviderError

from toscaparser.common.exception import ExceptionCollector


def get_full_facts_list():
    facts = list()
    for provider, elems in FACTS_BY_PROVIDER.items():
        facts.extend(elems.keys())
    return facts


def get_auth_params_dict():
    parameters = dict()
    for provider, params in AUTH_PARAM_FUNCS_BY_PROVIDER.items():
        parameters.update(params())
    return parameters


def combine_facts_from_ansible_params(provider, ansible_params):
    fact_keys = FACTS_BY_PROVIDER.get(provider)
    if not fact_keys:
        ExceptionCollector.appendException(UnspecifiedFactsParserForProviderError(
            what=provider
        ))
    ansible_facts_key_map = FACTS_MODULE_PARAMS_MAP_BY_PROVIDER.get(provider, {})
    ansible_facts = ansible_params['facts'] if ansible_params['facts'] else {}

    facts = dict()
    for fact_key, internal_keys in fact_keys.items():
        key = next(iter(fact_key.split("_fact", 1))) + 's'
        value = ansible_params[fact_key] if ansible_params[fact_key] else {}
        for k in internal_keys:
            if type(value) is dict:
                value = value.get(k, {})
        if type(value) is not list:
            ansible_facts_key = ansible_facts_key_map.get(fact_key)
            if ansible_facts_key:
                value = ansible_facts.get(ansible_facts_key, {})
        if type(value) is list:
            facts[key] = value

    return facts
