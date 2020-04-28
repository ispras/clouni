# Clouni
Cloud Unifier Tool for Service Orchestration

Clouni is a cloud application management tool based on OASIS standard 
[TOSCA](http://docs.oasis-open.org/tosca/TOSCA-Simple-Profile-YAML/v1.0/TOSCA-Simple-Profile-YAML-v1.0.html)

## Installation
Clouni requires Python 3.7 to be used.

To install Clouni is recommended to create virtual environment and install 
requirements in your environment. 

Installation command
~~~shell
cd $TOSCA_TOOL_HOME
python setup.py install
~~~

## Usage

Execute
~~~shell 
clouni --help
~~~
Output
~~~
usage: clouni [-h] --template-file <filename> [--validate-only]
                  [--provider PROVIDER] [--facts <filename>]

optional arguments:
  -h, --help            show this help message and exit
  --template-file <filename>
                        YAML template to parse.
  --validate-only       Only validate input template, do not perform
                        translation.
  --provider PROVIDER   Cloud provider name to execute ansible playbook in.
  --facts <filename>    Facts for cloud provider if provider parameter is
                        used.
~~~

Example
~~~shell
clouni --template-file tosca-server-example.yaml
~~~

## Adding new provider 

Template of project files structure: 
~~~
.ansible/
|-- plugins
|   |-- module_utils
|   |   |-- cloud_infra_by_tosca.py
toscatranslator/
|-- providers
|   |-- combined
|   |   |-- combined_facts.py
|   |   |-- combine_provider_resource.py
|   |-- <provider>
|   |   |-- provider_resource.py
|   |   |-- tosca_elements_map_to_provider.json
|   |   |-- TOSCA_<provider>_definition_1_0.yaml
~~~

The `<provider>` means the provider's unique nic. Adding new provider 
includes several steps.

### Prestep: considering main components of cloud 

There is set of common parameters to launch virtual machine. This 
parameters are manages in different ways by different providers and a 
unified by TOSCA.

* _private address_ - the primary private IP address assigned by the cloud 
provider that applications may use to access the Compute node.
* _public address_ - he primary public IP address assigned by the cloud 
provider that applications may use to access the Compute node.
* _networks/ports_: network names or ids or port names or ids or addresses 
* _host_: number of CPUs, disk size, RAM size or CPU frequency
* _endpoint_ - network access endpoint capability
  * _protocol_ - http, https, ftp, tcp, udp, etc
  * _port_ of endpoint 
  * _url path_ of endpoint's address if applicable for the protocol
  * _port name_ which endpoint should be bound to
  * _network name_ which endpoint should be bound to
  * _initiator_ - one of: source, target, peer
  * _IP address_ as propagated up by the associated node’s host (Compute) 
  container
  * if _secured_ connection
* _os_ - operating system parameters:
  * _architecture_ - x86_32, x86_64, etc.
  * _type_ - linux, aix, mac, windows, etc.
  * _distribution_ -  debian, fedora, rhel and ubuntu
  * _version_
* _scalable_: min, default, max of instances to launch
* _volumes_: local storages

### Step 1: Defining main components of cloud provider

Prestep results in set of virtual cloud resources containing required 
parameters (instances, images, security groups, etc.)

Define main components definitions in language specified by TOSCA. 

The template of definition file must be: 
~~~
tosca_definitions_version: tosca_simple_yaml_1_0
capability_types:
    <provider>.capabilities.Root:
        derived_from: tosca.capabilities.Root
    <...>
node_types:
    <provider>.nodes.Root:
        derived_from: tosca.nodes.Root
        capabilities:
            feature:
                type: <provider>.capabilities.Node
                occurrences: [ 1, 1 ]
        requirements:
            - dependency:
                capability: <provider>.capabilities.Node
                node: <provider>.nodes.Root
                relationship: <provider>.relationships.DependsOn
                occurrences: [ 0, UNBOUNDED ]
    <...>
relationship_types:
    <provider>.relationships.DependsOn:
        description: This type results in ordering of initializing objects.
        derived_from: tosca.relationships.DependsOn
        valid_target_types: [ <provider>.capabilities.Node ]
    <...>
~~~

Examples can be found in `toscatranslator/providers/<provider>` 
directories. 

### Step 2: Defining mapping between tosca.nodes.Compute and main components of cloud provider

This step is the declarative defining of mapping considered in Prestep 
using definitions from Step 1. 

This mapping represents in either JSON or YAML format. Further the rules 
to describe the mapping are provided. 

The parameters of TOSCA normative node type are determined as keys, and 
the parameters of the provider node types are determined as values. All 
parameters name must include the node type and the parameter section and 
name, which called _extended parameter name_. For example, 
`tosca.nodes.Compute.attributes.private_address`.

The values are represented in format, called _value format_. The value 
format can be of type list, map and string. If the value is of type map, 
then it's one of the following cases:

* keys are `parameter`, `value`, `keyname`: `parameter` contains the name 
of the specialized type parameter, the `value` contains the value of 
this parameter, `keyname` specialises the name of the node topology in 
which to add this parameter, `keyname` can be used to create several 
nodes of the same type. Example:
  ~~~
  tosca.nodes.Compute.capabilities.host.properties
             .num_cpus:
  parameter: openstack.nodes.Server.requirements
             .flavor.node_filter.properties.vcpus
  value: {self[value]}
  ~~~
* keys are `error`, `reason`: used if the parameter cannot be specified 
in TOSCA template for a certain reason.
* keys are `value`, `condition`, `facts`, `arguments`: used if `facts` 
need to be filtered for some value satisfying some `condition` and its 
`arguments`. Three values are supported by the condition key: `equals`, 
`contains`, `ip_contains`. Example:
  ~~~ 
  tosca.nodes.Compute.attributes.networks.*
                  .addresses:
  parameter: openstack.nodes.Server.requirements
                  .nics.node_filter.properties.id
  value: 
    value: network_id
    facts: openstack_subnet_facts
    condition: ip_contains
    arguments:
      - allocation_pool_start
      - allocation_pool_end
      - {self[value]}
  ~~~
* keys are `source`, `parameters`, `extra`, `value`, `executor`: used to 
add operation implementation and hence create a relationship, `source`
represents the name of ansible module or any other command or source
of a specific executor, `parameters` are the arguments of the source, 
`extra` is the extra info, if Ansible is used `parameters` are the 
arguments of module and `extra` are the extra parameters of the task,
`value` (#TODO), `executor` represents the configuration tool or some
another supported executor (ex. ansible, bash)    

**ATTENTION**. Please don't use reserved keys in you mapping values, 
ex. replace 'parameter' key by 'input_parameter'.

The interpreter also defines a variable `self` that can be used to store 
and read some values in a key-value format. For example:

~~~
tosca.nodes.Compute.endpoint.attributes.ip_address: 
  parameter: {self[buffer][security_group_rule][cidr_ip]}
  value: {self[value]}
tosca.nodes.Compute.endpoint.properties.initiator.target:
  parameter: amazon.nodes.SecurityGroup.properties.rules
  value:
    - {self[buffer][security_group_rule]}
~~~

There are also predefined values:
* `parameter` contains the extended name of TOSCA normative type parameter
* `value` contains the value defined by the key `parameter` in TOSCA 
template
* `name` contains the current node name

As a result, any updates of cloud API or new versions of TOSCA standard 
causes only minor changes in the interpreter cloud definitions, which 
simplifies the process of adding a new cloud provider support.