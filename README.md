# Clouni
Cloud Unifier Tool for Service Orchestration

Clouni is a cloud application management tool based on OASIS standard 
[TOSCA](http://docs.oasis-open.org/tosca/TOSCA-Simple-Profile-YAML/v1.0/TOSCA-Simple-Profile-YAML-v1.0.html)

## Michman

Use `michman-integration` branch to see Michman specific templates.

~~~shell
git checkout michman-integration
~~~

## Installation
Clouni requires Python 3 to be used.

To install Clouni is recommended to create virtual environment and install 
requirements in your environment. 
~~~shell
virtualenv -p /usr/bin/python3 $VIRTUALENV_HOME/clouni
~~~
It's recommended not to use `$ClOUNI_HOME` as your `$VIRTUALENV_HOME`

Install Clouni requirements in you virtual environment

~~~shell
source $VIRTUALENV_HOME/clouni/bin/activate
cd $CLOUNI_HOME
pip install -r requirements.txt
~~~

Installation command
~~~shell
cd $CLOUNI_HOME
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
              [--provider PROVIDER] [--output-file <filename>]
              [--configuration-tool CONFIGURATION_TOOL]

optional arguments:
  -h, --help            show this help message and exit
  --template-file <filename>
                        YAML template to parse.
  --validate-only       Only validate input template, do not perform
                        translation.
  --delete              Delete cluster
  --provider PROVIDER   Cloud provider name to execute ansible playbook in.
  --output-file <filename>
                        Output file
  --configuration-tool CONFIGURATION_TOOL
                        Configuration tool which DSL the template would be
                        translated to. Default value = "ansible"
  --async               Provider nodes should be created asynchronously
  --extra KEY=VALUE [KEY=VALUE ...]
                        Extra arguments for configuration tool scripts
~~~

#### Check full example of Clouni possibilities for OpenStack provider 
Small example of input: 
~~~
tosca_definitions_version: tosca_simple_yaml_1_0

topology_template:
  node_templates:
    server_kube_master:
      type: tosca.nodes.Compute
      capabilities:
        os:
          properties:
            architecture: x86_64
            type: ubuntu
            distribution: xenial
            version: 16.04
~~~

Topology template contains several node or relationship templates to create in a cloud. 
Templates can be of different types. 
The only type supported by Clouni is `Compute` as in the example. 
Other type are planned to be supported in the future.
##### Creating

~~~shell
clouni --template-file examples/tosca-server-example.yaml --cluster-name example --provider openstack
~~~
Clouni output is Ansible playbook. 
~~~
- hosts: localhost
  name: Create openstack cluster
  tasks:
  - os_image_facts: {}
    register: facts_result
  - register: tmp_value
    set_fact:
      target_objects: '{{ facts_result["ansible_facts"]["openstack_image"] }}'
  - set_fact:
      target_objects_8838: '{{ target_objects }}'
  - set_fact:
      input_facts: '{{ target_objects_8838 }}'
  - set_fact:
      input_args_5697:
      - - name
        - properties
      - architecture: x86_64
        distribution: xenial
        type: ubuntu
        version: 16.04
  - set_fact:
      input_args: '{{ input_args_5697 }}'
  - include: contains.yaml
  - register: tmp_value
    set_fact:
      name: '{{ matched_object["name"] }}'
  - set_fact:
      name_1511: '{{ name }}'
  - file:
      path: '{{ playbook_dir }}/id_vars_example.yaml'
      state: absent
  - file:
      path: '{{ playbook_dir }}/id_vars_example.yaml'
      state: touch
  - name: Create OpenStack component server
    os_server:
      config_drive: false
      image: '{{ name_1511 }}'
      name: server_kube_master
    register: server_kube_master_server
  - lineinfile:
      line: 'server_kube_master_server: {{ server_kube_master_server.id }}'
      path: '{{ playbook_dir }}/id_vars_example.yaml'
    when: server_kube_master_server.id is defined
  - fail:
      msg: Variable server_kube_master_server.id is undefined! So it will not be deleted
    ignore_errors: true
    when: server_kube_master_server.id is undefined
~~~
##### Deleting
To generate playbook with the same input template, just add a --delete command
~~~
clouni --template-file examples/tosca-server-example.yaml --cluster-name example --provider openstack --delete
~~~
Clouni output
~~~
- hosts: localhost
  name: Delete openstack cluster
  tasks:
  - include_vars: '{{ playbook_dir }}/id_vars_example.yaml'
  - name: Delete OpenStack component server
    os_server:
      name: '{{ server_kube_master_server }}'
      state: absent
    when: server_kube_master_server is defined
  - file:
      path: '{{ playbook_dir }}/id_vars_example.yaml'
      state: absent
~~~
Ansible playbook can be executed to create or delete an instance
~~~
ansible-playbook <playbook_name>.yaml
~~~
After the execution of creating playbook, the file **id_vars_<cluster-name>.yaml** will be created. This file contains all resources ids. Deleting playbook uses ids from this file and after successful deleting removes file too.

**ATTENTION** Most of providers require authentication for using there resources. 
Authentication is users responsibility. For example, to use OpenStack
you must download your OpenStack RC file and `source` it. 
After that user is able to execute Ansible playbook. 

During the Clouni execution it doesn't send or receive any information from cloud
or Internet. 

Generated script consists of two parts:
1. Get cloud information and choosing specific cloud parameters for meeting requirements.
2. Create cloud resources

For example to create OpenStack server cloud image name and flavor must be specified. 

## Adding new provider 

Template of project files structure: 
~~~
.ansible/
|-- plugins
|   |-- module_utils
|   |   |-- cloud_infra_by_tosca.py
toscatranslator/
|-- providers
|   |-- <provider>
|   |   |-- provider.cfg
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
nodes of the same type. Be attentive and sure you don't set existing names.
Example:
  ~~~
  tosca.nodes.Compute.capabilities.host.properties
             .num_cpus:
  parameter: openstack.nodes.Server.requirements
             .flavor.node_filter.properties.vcpus
  value: {self[value]}
  ~~~
* keys are `error`, `reason`: used if the parameter cannot be specified 
in TOSCA template for a certain reason.
  
* keys are `source`, `parameters`, `extra`, `value`, `executor`: used to 
add operation implementation and hence create a relationship, `source`
represents the name of ansible module or any other command or source
of a specific executor or the file name to execute, 
`parameters` are the arguments of the source, 
`extra` is the extra info, if Ansible is used `parameters` are the 
arguments of module and `extra` are the extra parameters of the task,
`value` represents variable name passing after script execution, 
it can be unnecessary but must be defined any way,
`executor` represents the configuration tool or some
another supported executor (ex. ansible, python). Example:
  ~~~
    - source: set_fact
    executor: ansible
    parameters:
      new_var: 1
    value: tmp_value
  # example with python script 
    - source: transform_units
      parameters:
        source_value: "{self[value]}"
        is_without_b: True
      executor: python
      value: default
  ~~~
  
* keys are `value`, `condition`, `facts`, `arguments`, `executor`: used if the value must 
be first chosen from existing cloud resources, `facts` represents the source which is use to get list 
of cloud resources paramters, facts need to be filtered for some value satisfying some `condition` and its 
`arguments`. Three conditions are supported: `equals`, `contains`, `ip_contains`. Example:
  ~~~ 
  tosca.nodes.Compute.attributes.networks.*
                  .addresses:
  parameter: openstack.nodes.Server.requirements
                  .nics.node_filter.properties.id
  value: 
    - value: network_id
    condition: ip_contains
    facts: os_subnets_facts.ansible_facts.openstack_subnets
    executor: ansible
    arguments:
    - allocation_pool_start
    - allocation_pool_end
    - "{self[value]}"
  ~~~ 

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

**ATTENTION** You shouldn't use multiple type deriviation from each other 
except default deriviation from Root. As it's unknown actions to resolve
dependencies from parents. 


### Step 3: Provider configuration file

Every provider is configured with configuration file which can be one 
the following (sorted by priority):
1. `<provider>.cfg` in the working directory where user executes Clouni
1. `toscatranslator/providers/<provider>/provider.cfg` in `$TOSCA_HOME`
1. `toscatranslator/providers/<provider>/<provider>.cfg` in `$TOSCA_HOME`

`<provider>` means provider's nic in Clouni 

It has required settings for Clouni execution: 
~~~
[main]
tosca_elements_definition_file = TOSCA_openstack_definition_1_0.yaml
tosca_elements_map_file = tosca_elements_map_to_openstack.yaml
~~~

* `tosca_elements_definition_file` points to the name of the file created in Step 1
* `tosca_elements_map_file` points to the name of the file created in Step 2

Paths to the specified files must be absolute or from the directory where 
provider configuration file is located.

Configuration tools are configured for every provider in provider configuration file.
Settings must be in section names with the configuration tool. For example:

~~~
[ansible]
module_prefix = os_
module_description = Create OpenStack component
~~~ 

* `module_prefix` is added to the name of provider component type, for example if openstack.nodes.Server is created 
then `os_server` Ansible module will be used 
* `module_description` is added as a description to the Ansible module

Every configuration tool can have it's own setting parameters

If the mapping from Step 2 uses TOSCA `node_filter` 
([example](http://docs.oasis-open.org/tosca/TOSCA-Simple-Profile-YAML/v1.0/os/TOSCA-Simple-Profile-YAML-v1.0-os.html#_Toc471725299)), 
then the following section must be specified for every supported configuration tool:

~~~
[ansible.node_filter]
node_filter_source_prefix = os_
node_filter_source_postfix = _facts
node_filter_exceptions =
    subnet = os_subnets_facts
node_filter_inner_variable =
    image = ansible_facts,openstack_image
    flavor = ansible_facts,openstack_flavors
~~~

* `node_filter_source_prefix`, `node_filter_source_postfix` is added to the name of provider component type, 
for example if openstack.nodes.Server is need to be filtered 
then `os_server_facts` Ansible module will be used
* `node_filter_exceptions` is of key = value format and is used if prefix and postfix is not enough,
for example openstack.nodes.Subnet would be filtered by `os_subnets_facts` not `os_subnet_facts` 
* `node_filter_inner_variable` is used to specify JSON keys if facts were received not as list,
for example facts for openstack.nodes.Image would be received by module `os_image_facts` and the return value
would be `image_facts = output_os_image_facts["ansible_facts"]["openstack_image"]`

## Filter conditions

Conditions used in the mapping  must be implemented for every configuration tool and be located in 
`toscatranslator/providers/<provider>/artifacts` directory

### Ansible conditions

Here the *fact* is the key-value object, where keys are the parameters of any cloud resource
and the value are the values of that parameters. *Facts* is the list of *fact* 

When using Ansible configuration tool every condition artifact must have '.yaml' extension and consist 
onl Ansible tasks for filtering facts. 

If developer implement condition artifact, he must use variables `input_facts`, `input_args` as predefined
and define two variables `matched_object` and `matched_objects` in the end. 
Variable `matched_objects` contains list of all matched facts and `matched_object` should contain one of them.

**ATTENTION** If there are more then one matched facts the last is taken as matched fact
 