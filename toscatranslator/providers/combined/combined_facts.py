
openstack_facts = dict(
    openstack_flavor_facts=['ansible_facts', 'openstack_flavors'],
    openstack_image_facts=['ansible_facts', 'openstack_image'],
    openstack_network_facts=['ansible_facts', 'openstack_networks'],
    openstack_port_facts=['ansible_facts', 'openstack_ports'],
    openstack_server_facts=['ansible_facts', 'openstack_servers'],
    openstack_subnet_facts=['ansible_facts', 'openstack_subnets']
)


amazon_facts = dict(
    ec2_eni_facts=['network_interfaces'],
    ec2_ami_facts=['images'],
    ec2_vpc_facts=['vpcs'],
    ec2_subnet_facts=['subnets'],
    ec2_instance_type_facts=['ansible_facts', 'amazon_instance_types']
)

amazon_fact_name_by_node_name = dict(
    ElasticNetworkInterface='ec2_eni_facts',
    Image='ec2_ami_facts',
    VirtualPrivateCloud='ec2_vpc_facts',
    VirtualPrivateCloudSubnet='ec2_subnet_facts'
)

openstack_fact_name_by_node_name = dict(
    Flavor='openstack_flavor_facts',
    Image='openstack_image_facts',
    Network='openstack_network_facts',
    Port='openstack_port_facts',
    Server='openstack_server_facts',
    Subnet='openstack_subnet_facts'
)
FACTS_BY_PROVIDER = dict(
    amazon=amazon_facts,
    openstack=openstack_facts
)

FACT_NAME_BY_NODE_NAME = dict(
    amazon=amazon_fact_name_by_node_name,
    openstack=openstack_fact_name_by_node_name
)