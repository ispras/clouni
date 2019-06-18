##########################################################################
# FACTS_BY_PROVIDER
##########################################################################

amazon_facts = dict(
    ec2_eni_facts=['network_interfaces'],
    ec2_ami_facts=['images'],
    ec2_vpc_facts=['vpcs'],
    ec2_security_group_facts=['security_groups'],  # TODO
    ec2_subnet_facts=['subnets'],
    ec2_instance_facts=['instances'],  # TODO
    ec2_instance_type_facts=['ansible_facts', 'amazon_instance_types']
)

openstack_facts = dict(
    openstack_flavor_facts=['ansible_facts', 'openstack_flavors', 'flavor'],
    openstack_image_facts=['ansible_facts', 'openstack_image', 'image'],
    openstack_network_facts=['ansible_facts', 'openstack_networks', 'network'],
    openstack_port_facts=['ansible_facts', 'openstack_ports'],
    openstack_server_facts=['ansible_facts', 'openstack_servers'],
    openstack_subnet_facts=['ansible_facts', 'openstack_subnets']
)

FACTS_BY_PROVIDER = dict(
    amazon=amazon_facts,
    openstack=openstack_facts
)

##########################################################################
# FACT_NAME_BY_NODE_NAME
##########################################################################

amazon_fact_name_by_node_name = dict(
    elastic_network_interface='ec2_eni_facts',
    image='ec2_ami_facts',
    instance=['ec2_instance_facts', 'ec2_instance_type_facts'],
    virtual_private_cloud='ec2_vpc_facts',
    virtual_private_cloud_subnet='ec2_subnet_facts',
    security_group='ec2_security_group_facts'
)

openstack_fact_name_by_node_name = dict(
    flavor='openstack_flavor_facts',
    image='openstack_image_facts',
    network='openstack_network_facts',
    port='openstack_port_facts',
    server='openstack_server_facts',
    subnet='openstack_subnet_facts'
)

FACT_NAME_BY_NODE_NAME = dict(
    amazon=amazon_fact_name_by_node_name,
    openstack=openstack_fact_name_by_node_name
)

##########################################################################
# FACTS REFACTORING
##########################################################################
refactoring_ami_keys = dict(
    id=['image_id']
)

refactoring_eni_keys = dict(
    eni_id=['network_interface_id'],
    security_groups=['groups']
)

refactoring_vpc_facts = dict(
    name=['tags', 'Name'],
    vpc_id=['id']
)

refactoring_security_group_facts = dict(
    # TODO
)

refactoring_ec2_subnet_keys = dict(
    cidr=['cidr_block'],
    map_public=['map_public_ip_on_launch']
)

refactoring_ec2_instance_facts = dict(
    network=['network_interfaces'],
    security_groups=['security_groups', 'id'],
    vpc_subnet_id=['subnet_id']
)

refactoring_instance_type_keys = dict(
    apiname=['apiname'],
    memory=['memory'],
    vcpus=['vcpus'],
    storage=['storage']
)

refactoring_flavor_keys = dict(

)
refactoring_image_keys = dict(

)
refactoring_network_keys = dict(
    external=['router:external'],
    provider_network_type=['provider:network_type'],
    provider_physical_network=['provider:physical_network'],
    provider_segmentation_id=['provider:segmentation_id']
)
refactoring_port_keys = dict(
    network=['network_id'],
    vnic_type=['binding:vnic_type'],
    ip_address=['fixed_ips', 'ip_address']
)
refactoring_server_keys = dict(
    meta=['metadata'],
    userdata=['user_data'],
    flavor=['flavor', 'id'],
    floating_ips=['interface_ip'],
    image=['image', 'id'],
    network=['networks'],
    nics=['networks'],
    security_groups=['security_groups', 'name'],
    volumes=['volumes', 'id']
)
refactoring_subnet_keys = dict(
    allocation_pool_end=['allocation_pools', 'end'],
    allocation_pool_start=['allocation_pools', 'start'],
    network_name=['network_id'],
    network_id=['network_id']
)

REFACTORING_FACT_KEYS = dict(
    ec2_eni_facts=refactoring_eni_keys,
    ec2_ami_facts=refactoring_ami_keys,
    ec2_vpc_facts=refactoring_vpc_facts,
    ec2_security_group_facts=refactoring_security_group_facts,
    ec2_subnet_facts=refactoring_ec2_subnet_keys,
    ec2_instance_facts=refactoring_ec2_instance_facts,
    ec2_instance_type_facts=refactoring_instance_type_keys,

    openstack_flavor_facts=refactoring_flavor_keys,
    openstack_image_facts=refactoring_image_keys,
    openstack_network_facts=refactoring_network_keys,
    openstack_port_facts=refactoring_port_keys,
    openstack_server_facts=refactoring_server_keys,
    openstack_subnet_facts=refactoring_subnet_keys

)
