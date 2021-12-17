TOSCA = 'tosca'

(AMAZON, OPENSTACK, KUBERNETES) = ('amazon', 'openstack', 'kubernetes')
PROVIDERS = (AMAZON, OPENSTACK, KUBERNETES)

(ANSIBLE) = ('ansible')
(KUBERNETES) = ('kubernetes')

(GET_INPUT, GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT, GET_NODES_OF_TYPE, GET_ARTIFACT) \
    = ('get_input', 'get_property', 'get_attribute', 'get_operation_output', 'get_nodes_of_type', 'get_artifact')
GET_FUNCTIONS = (GET_INPUT, GET_PROPERTY, GET_ATTRIBUTE, GET_OPERATION_OUTPUT, GET_NODES_OF_TYPE, GET_ARTIFACT)

(SELF, SOURCE, SOURCES, TARGET, TARGETS, HOST) \
    = ('SELF', 'SOURCE', 'SOURCES', 'TARGET', 'TARGETS', 'HOST')
TEMPLATE_REFERENCES = (SELF, SOURCE, SOURCES, TARGET, TARGETS, HOST)

(OCCURRENCES, NODE, NODE_FILTER, CAPABILITY, RELATIONSHIP, DEFAULT) \
    = ('occurrences', 'node', 'node_filter', 'capability', 'relationship', 'default')
REQUIREMENT_KEYS = (NODE, NODE_FILTER, OCCURRENCES, CAPABILITY, RELATIONSHIP)

(TYPE, DESCRIPTION, METADATA, DIRECTIVES, PROPERTIES, ATTRIBUTES, CAPABILITIES, REQUIREMENTS, ARTIFACTS, INTERFACES) \
    = ('type', 'description', 'metadata', 'directives', 'properties', 'attributes', 'capabilities', 'requirements', 'artifacts', 'interfaces')
NODE_TEMPLATE_KEYS = (TYPE, DESCRIPTION, METADATA, DIRECTIVES, PROPERTIES, ATTRIBUTES, CAPABILITIES, REQUIREMENTS, ARTIFACTS, INTERFACES)
DERIVED_FROM = 'derived_from'

(NAME, ID) = ('name', 'id')
(NAME_SUFFIX, ID_SUFFIX) = ('_name', '_id')
REQUIREMENT_DEFAULT_PARAMS = (NAME, ID)

(TOSCA_DEFINITIONS_VERSION, IMPORTS, NODE_TYPES, CAPABILITY_TYPES, RELATIONSHIP_TYPES, DATA_TYPES, INTERFACE_TYPES, POLICY_TYPES, GROUP_TYPES) \
    = ('tosca_definitions_version', 'imports', 'node_types', 'capability_types', 'relationship_types', 'data_types', 'interface_types', 'policy_types', 'group_types')
SERVICE_TEMPLATE_KEYS = (IMPORTS, NODE_TYPES, CAPABILITY_TYPES, RELATIONSHIP_TYPES, DATA_TYPES, INTERFACE_TYPES, POLICY_TYPES, GROUP_TYPES)

(NODE_TEMPLATES, TOPOLOGY_TEMPLATE, RELATIONSHIP_TEMPLATES) = ('node_templates', 'topology_template', 'relationship_templates')

MAPPING_VALUE_KEYS = (ERROR, REASON, PARAMETER, VALUE, CONDITION, FACTS, ARGUMENTS, SOURCE, PARAMETERS, EXTRA, EXECUTOR, KEYNAME) = \
    ('error', 'reason', 'parameter', 'value', 'condition', 'facts', 'arguments', 'source', 'parameters', 'extra', 'executor', 'keyname')

FACTS_MAPPING_VALUE_STRUCTURE = (VALUE, CONDITION, FACTS, ARGUMENTS, EXECUTOR)
PARAMETER_MAPPING_VALUE_STRUCTURE = (PARAMETER, VALUE)

SUPPORTED_MAPPING_VALUE_STRUCTURE = ((ERROR, REASON),
                                     PARAMETER_MAPPING_VALUE_STRUCTURE,
                                     FACTS_MAPPING_VALUE_STRUCTURE,
                                     (SOURCE, PARAMETERS, VALUE, EXECUTOR))

(NODES, RELATIONSHIPS, DATATYPES, POLICIES, GROUPS) = ("nodes", "relationships", "datatypes", "policies", "groups")
ELEMENT_TYPES = (NODES, CAPABILITIES, RELATIONSHIPS, DATATYPES, INTERFACES, ARTIFACTS, POLICIES, GROUPS)

(IMPLEMENTATION, INPUTS) = ("implementation", "inputs")

(OUTPUTS) = ("outputs")

(ROOT) = ("Root")

(CLOUNI) = ('clouni')

(TOSCA_ELEMENTS_DEFINITION_FILE, DEFAULT_ARTIFACTS_DIRECTORY, TOSCA_ELEMENTS_MAP_FILE) = \
    ('tosca_elements_definition_file', 'default_artifacts_directory', 'tosca_elements_map_file')