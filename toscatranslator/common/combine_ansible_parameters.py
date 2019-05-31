# NOTE: The same libraries must be imported again in ansible module file
try:
    from ansible.module_utils.openstack import openstack_full_argument_spec
    from ansible.module_utils.ec2 import ec2_argument_spec

    HAS_ARGUMENT_LIBS = True
except:
    HAS_ARGUMENT_LIBS = False

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

AUTH_PARAM_FUNCS_BY_PROVIDER = dict(
    amazon=ec2_argument_spec,
    openstack=openstack_full_argument_spec
)

FACTS_MODULE_PARAMS_MAP_BY_PROVIDER = dict(
    amazon=amazon_facts_module_params_map,
    openstack=openstack_facts_module_params_map
)
