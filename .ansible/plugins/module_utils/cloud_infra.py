from translator.common.ansible_parameters import get_full_facts_list, get_auth_params_dict


def cloud_infra_full_argument_spec(**kwargs):
    spec = dict()
    facts_list = get_full_facts_list()
    facts_dict = dict()
    for fact in facts_list:
        # facts_dict[fact] = dict(required=False, type='list')
        facts_dict[fact] = dict(required=False)
    spec.update(facts_dict)
    spec.update(get_auth_params_dict())
    spec.update(kwargs)
    return spec

