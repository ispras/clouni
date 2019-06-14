# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#########################################################################################################
#                                       IMPORTED PARAMETERS
#########################################################################################################

# TODO add arguments if new provider is being added

from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.ec2 import ec2_argument_spec

AUTH_PARAM_FUNCS_BY_PROVIDER = dict(
    amazon=ec2_argument_spec,
    openstack=openstack_full_argument_spec
)

#########################################################################################################
#                                       DO NOT TOUCH ZONE
#########################################################################################################


def get_auth_params_dict():
    parameters = dict()
    for provider, params in AUTH_PARAM_FUNCS_BY_PROVIDER.items():
        parameters.update(params())
    return parameters


def get_full_facts_list():
    import importlib
    facts_by_provider = importlib.import_module('toscatranslator.providers.combined', 'combined_facts')\
        .FACTS_BY_PROVIDER
    facts = list()
    for provider, elems in facts_by_provider.items():
        facts.extend(elems.keys())
    return facts


def combine_facts_from_ansible_params(provider, ansible_params):
    if provider is None:
        return dict()
    import importlib
    facts_by_provider = importlib.import_module('toscatranslator.providers.combined', 'combined_facts')\
        .FACTS_BY_PROVIDER
    fact_keys = facts_by_provider.get(provider)
    if not fact_keys:
        return None

    facts = dict()
    for fact_key, internal_keys in fact_keys.items():
        value_from_params = ansible_params.get(fact_key) or {}
        value_from_facts = ansible_params.get('facts') or {}
        for k in internal_keys:
            if type(value_from_params) is dict:
                temp_v = value_from_params.get(k, {})
                if temp_v is not None:
                    value_from_params = value_from_params
            if type(value_from_facts) is dict:
                temp_v = value_from_facts.get(k, {})
                if temp_v is not None:
                    value_from_facts = value_from_facts

        if type(value_from_params) is list:
            facts[fact_key] = value_from_params
        else:
            facts[fact_key] = []

    return facts


def cloud_infra_full_argument_spec(**kwargs):
    spec = dict()
    facts_list = get_full_facts_list()
    facts_dict = dict()
    for fact in facts_list:
        facts_dict[fact] = dict(required=False)  # type can be either list or dict
    spec.update(facts_dict)
    spec.update(get_auth_params_dict())
    spec.update(kwargs)
    return spec
