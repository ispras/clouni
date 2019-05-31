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

from ansible.module_utils.openstack import openstack_full_argument_spec
from ansible.module_utils.ec2 import ec2_argument_spec

# TODO place to fulfil if new provider is added

openstack_facts = dict(openstack_flavor_facts=['ansible_facts', 'openstack_flavors'],
                       openstack_image_facts=['ansible_facts', 'openstack_image'],
                       openstack_network_facts=['ansible_facts', 'openstack_networks'],
                       openstack_port_facts=['ansible_facts', 'openstack_ports'],
                       openstack_server_facts=['ansible_facts', 'openstack_servers'],
                       openstack_subnet_facts=['ansible_facts', 'openstack_subnets']
                       )

openstack_facts_module_params_map = dict(
    openstack_flavor_facts='openstack_flavors',
    openstack_image_facts='openstack_image',
    openstack_network_facts='openstack_networks',
    openstack_port_facts='openstack_ports',
    openstack_server_facts='openstack_servers',
    openstack_subnet_facts='openstack_subnets'
)

amazon_facts = dict(ec2_eni_facts=['network_interfaces'],
                    ec2_ami_facts=['images'],
                    ec2_vpc_facts=['vpcs'],
                    ec2_subnet_facts=['subnets'],
                    ec2_instance_type_facts=['ansible_facts', 'amazon_instance_types'])

amazon_facts_module_params_map = dict(
    ec2_instance_type_facts='amazon_instance_types'
)

# IMPORTED PARAMETERS


FACTS_BY_PROVIDER = dict(
    amazon=amazon_facts,
    openstack=openstack_facts
)

FACTS_MODULE_PARAMS_MAP_BY_PROVIDER = dict(
    amazon=amazon_facts_module_params_map,
    openstack=openstack_facts_module_params_map
)

AUTH_PARAM_FUNCS_BY_PROVIDER = dict(
    amazon=ec2_argument_spec,
    openstack=openstack_full_argument_spec
)

# DO NOT TOUCH ZONE


def get_auth_params_dict():
    parameters = dict()
    for provider, params in AUTH_PARAM_FUNCS_BY_PROVIDER.items():
        parameters.update(params())
    return parameters


def get_full_facts_list():
    facts = list()
    for provider, elems in FACTS_BY_PROVIDER.items():
        facts.extend(elems.keys())
    return facts


def combine_facts_from_ansible_params(provider, ansible_params):
    if provider is None:
        return dict()
    fact_keys = FACTS_BY_PROVIDER.get(provider)
    if not fact_keys:
        return None
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
