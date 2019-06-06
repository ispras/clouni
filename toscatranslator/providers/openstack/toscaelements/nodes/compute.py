from toscatranslator.providers.common.tosca_node_for_translate import ToscaNodeForTranslate

from netaddr import IPRange, IPAddress

from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import InappropriateParameterValueError


class ToscaComputeNode(ToscaNodeForTranslate):
    def __init__(self, node, facts):
        name = node.name
        template = node.entity_tpl
        super(ToscaComputeNode, self).__init__(name, template, facts)
        attributes = self.template.get("attributes", {})
        # capability server
        self.server = dict(
            properties=dict(
                name=self.name
            )
        )
        # node port
        self.port = self._port(attributes.get("private_address"))
        # floating ip
        self.floating_ip = self._floating_ip(attributes.get("public_address"))
        # requirements nics
        networks = attributes.get('networks')
        ports = attributes.get('ports')
        self.nics_by_name, self.nics_by_id, self.nics_by_mac_address = self._nics(networks, ports)
        capabilities = self.template.get('capabilities', {})
        # flavor parameter
        self.flavor = self._flavor(capabilities.get('host', {}).get('properties'))
        # security group and rules
        self.security_group_rule = self._security_group_rule(capabilities.get('endpoint').get('properties'),
                                                             capabilities.get('endpoint').get('attributes').get('ip_address'))
        # image filter
        self.image_name = self._image_name(capabilities.get('os', {}).get('properties'))
        # volume requirement
        # TODO: make multiple volumes
        local_storage = next(iter(self.template.get('requirements', {})), {}).get('local_storage', {})
        self.volume_size = self._volume_size(local_storage.get('node_filter', {}).get('properties', {}).get('size'))

        self.node_templates = self.construct_node_templates()

    def openstack_elements(self):
        return self.node_templates

    def construct_node_templates(self):
        node_templates = dict()
        node_templates[self.name] = dict(
            type='openstack.nodes.Server',
            capabilities=dict(
                self=self.server
            )
        )
        if self.port:
            node_templates[self.name+'_port_0'] = dict(
                type='openstack.nodes.Port',
                capabilities=dict(
                    self=dict(
                        properties=self.port
                    )
                )
            )
        if self.floating_ip:
            node_templates[self.name + '_floating_ip'] = self.floating_ip
            node_templates[self.name + '_floating_ip']['type'] = 'openstack.nodes.FloatingIp'
        requirements = []
        for nic_name in self.nics_by_name:
            requirements.append(dict(
                nics=dict(
                    node_filter=dict(
                        capabilities=dict(
                            self=dict(
                                properties=dict(
                                    name=nic_name
                                )
                            )
                        )
                    )
                )
            ))
        for nic_id in self.nics_by_id:
            requirements.append(dict(
                nics=dict(
                    node_filter=dict(
                        capabilities=dict(
                            self=dict(
                                properties=dict(
                                    id=nic_id
                                )
                            )
                        )
                    )
                )
            ))

        for nic_mac in self.nics_by_mac_address:
            requirements.append(dict(
                nics=dict(
                    node_filter=dict(
                        capabilities=dict(
                            self=dict(
                                properties=dict(
                                    mac_address=nic_mac
                                )
                            )
                        )
                    )
                )
            ))
        if self.flavor:
            requirements.append(dict(
                flavor=dict(
                    node_filter=dict(
                        capabilities=dict(
                            self=dict(
                                properties=self.flavor
                            )
                        )
                    )
                )
            ))
        if self.security_group_rule:
            node_templates[self.name+'_security_group'] = dict(
                type='openstack.nodes.SecurityGroup',
                properties=dict(
                    name=self.name+'_security_group'
                )
            )
            node_templates[self.name+'_security_group_rule_0'] = dict(
                type='openstack.nodes.SecurityGroupRule',
                properties=self.security_group_rule,
                requirements=[dict(
                    security_group=self.name+'_security_group'
                )]
            )
        if self.image_name:
            requirements.append(dict(
                image=dict(
                    node_filter=dict(
                        capabilities=dict(
                            self=dict(
                                properties=dict(
                                    name=self.image_name
                                )
                            )
                        )
                    )
                )
            ))
        if self.volume_size:
            requirements.append(dict(
                volumes=dict(
                    node_filter=dict(
                        properties=dict(
                            size=self.volume_size
                        )
                    )
                )
            ))
        if len(requirements) > 0:
            node_templates[self.name]['requirements'] = requirements

        return node_templates

    def _port(self, address):
        """
        Create a port from private address
        :param address: example: 192.168.24.5
        :return: example:

            fixed_ips:
              - <internal_network_name>: 192.168.24.5
        """
        if not address:
            return None
        network = self.find_network_by_ip(address=address)
        if not network:
            ExceptionCollector.appendException(InappropriateParameterValueError(
                what='private_address'
            ))
        if network['router:external']:
            ExceptionCollector.appendException(InappropriateParameterValueError(
                what='private_address'
            ))
        network_name = network['name']
        port = dict(
            fixed_ips=[dict()]
        )
        port['fixed_ips'][0][network_name] = address

        return port

    def _floating_ip(self, address):
        """
        Create floating ip from public_address
        :param address: example: 10.100.115.4
        :return: example:
            properties:
              floating_ip_address: 10.100.115.4
            requirements:
            - network:
                node_filter:
                  name: <network_name>
            - server: instance
        """
        if not address:
            return None
        network = self.find_network_by_ip(address=address)
        if not network:
            ExceptionCollector.appendException(InappropriateParameterValueError(
                what='public_address'
            ))
        if not network['router:external']:
            ExceptionCollector.appendException(InappropriateParameterValueError(
                what='public_address'
            ))
        floating_ip = dict(
            properties=dict(
                floating_ip_address=address
            ),
            requirements=[
                dict(
                    network=dict(
                        node_filter=dict(
                            properties=dict(
                                name=network['name']
                            )
                        )
                    )
                ),
                dict(
                    server=self.name
                )
            ]
        )
        return floating_ip

    def _nics(self, networks, ports):
        """
        Find existing networks and ports
        :param networks: example:
            some_net:
              network_name: internal
            another_net:
              network_id: 12345
            one_more_net:
              addresses: [10.100.115.0]
        :param ports: example:
            some_port:
              port_name: some_port
            another_port:
              port_id: another1port
            one_more_port:
              network_id: 1more2port
            second_more_port:
              mac_address: 00:00:00:00:00
            port_by_address:
              addresses: []
        :return: example:
          nics_by_id = [12345, another1port, 1more2port]
          nics_by_name = [internal, some_port, some_net_with_address]
          nics_by_mac_address = [00:00:00:00:00]
        """
        available_keys = {'network_name', 'network_id', 'port_name', 'port_id', 'mac_address'}
        by_keys = dict(
            network_name='name',
            network_id='id',
            addresses='',
            port_name='name',
            port_id='id',
            mac_address='mac_address'
        )
        nics_by = dict(
            name=set(),
            id=set(),
            mac_address=set()
        )
        for _, net in networks.items():
            key = next(iter(net.keys()))
            if key in available_keys:
                nics_by[by_keys[key]].add(net[key])
            elif key == 'addresses':
                addresses = net[key]
                network = self.find_network_by_ip(addresses=addresses)
                if not network:
                    ExceptionCollector.appendException(InappropriateParameterValueError(
                        what='addresses'
                    ))
                nics_by['name'].add(network['name'])

        for _, port in ports.items():
            key = next(iter(port.keys()))
            if key in available_keys:
                nics_by[by_keys[key]].add(port[key])
            elif key == 'addresses':
                addresses = port[key]
                network = self.find_network_by_ip(addresses=addresses)
                if not network:
                    ExceptionCollector.appendException(InappropriateParameterValueError(
                        what='addresses'
                    ))
                nics_by['name'].add(network['name'])

        return nics_by['name'], nics_by['id'], nics_by['mac_address']

    def _flavor(self, host_props):
        """
        Rename parameters to find existing flavor
        :param host_props: example:
            num_cpus: 2
            disk_size: 10 GiB
            mem_size: 1024 MiB
        :return:
            vcpus: 2
            disk: 10 GiB
            ram: 1024 MiB
        """
        if not host_props:
            return None
        flavor = dict()
        vcpus = host_props.get('num_cpus')
        disk = host_props.get('disk_size')
        ram = host_props.get('mem_size')
        if vcpus:
            flavor['vcpus'] = vcpus
        if disk:
            flavor['disk'] = disk
        if ram:
            flavor['ram'] = ram
        return flavor

    def _security_group_rule(self, props, address):
        """
        Make security group from endpoint parameters to create
        :param props: example:
            protocol: tcp
            port: 1
            port_name: name_port # update existing port not available
            network_name: name_network # update existing network not available
            initiator: target
            ports: # not implemented
              protocol: tcp
              target: 2
              target_range: [2, 3]
              source: 3
              source_range: [3, 4]
        :param address: example
            10.100.115.30
        :return: example
            protocol: tcp
            port_range_min: 1
            port_range_max: 1
            direction: ingress
        """
        if not props:
            return None
        if props.get('ports'):
            ExceptionCollector.appendException(NotImplementedError('Property "ports" in "endpoint" capability '
                                                                   'is not implemented yet'))
        # if props.get('port_name') or props.get('network_name'):
            # TODO make warning from exception
            # ExceptionCollector.appendException(NotImplementedError('Updating existing elements is not available yet. '
            #                                                        'Please do not use "port_name" '
            #                                                        'or "network_name" properties for endpoint'))
        protocol = props.get('protocol')
        port_range = props.get('port')
        direction = props.get('initiator')
        if direction:
            direction = direction.replace('source', 'egress').replace('target', 'ingress')
        remote_ip_prefix = address

        security_group_rule = dict()
        if protocol:
            security_group_rule['protocol'] = protocol
        if port_range:
            security_group_rule['port_range_min'] = port_range
            security_group_rule['port_range_max'] = port_range
        if direction:
            security_group_rule['direction'] = direction
        if remote_ip_prefix:
            security_group_rule['remote_ip_prefix'] = remote_ip_prefix

        return security_group_rule

    def _image_name(self, os_props):
        """
        Find image by operating system properties
        :param os_props: example:
            architecture: x86_64
            type: ubuntu
            distribution: xenial
            version: 16.04.6
        :return: image name
        """
        if not os_props:
            return None
        images = self.facts['images']
        arch = os_props.get('architecture', '')
        type_os = os_props.get('type', '')
        distr = os_props.get('distribution', '')
        ver = str(os_props.get('version', ''))
        for image in images:
            image_str = str(image['properties'].values()) + image['name']
            if arch in image_str and type_os in image_str and distr in image_str and ver in image_str:
                return image['name']
        ExceptionCollector.appendException(InappropriateParameterValueError(
            what='os'
        ))

    def _volume_size(self, size):
        return size

    def find_network_by_ip(self, address=None, addresses=[]):
        """
        Find the network with subnet which contains ip address
        :param addresses: list of str
        :param address: str
        :return: dict
        """
        subnets = self.facts['subnets']
        network_id = None
        ip_addresses = []
        if address:
            ip_addresses.append(IPAddress(address))
        for addr in addresses:
            ip_addresses.append(IPAddress(addr))
        for subnet in subnets:
            allocation_pools = subnet['allocation_pools']
            # TODO: make it wark with multiple allocation pools
            allocation_pool = next(iter(allocation_pools))
            start_ip = allocation_pool['start']
            end_ip = allocation_pool['end']
            ip_range = IPRange(start_ip, end_ip)
            fit = True
            for ip_addr in ip_addresses:
                if ip_addr not in ip_range:
                    fit = False
                    break
            if fit:
                network_id = subnet['network_id']

        if not network_id:
            return None
        networks = self.facts['networks']
        network = next(obj for obj in networks if obj['id'] == network_id)

        return network
