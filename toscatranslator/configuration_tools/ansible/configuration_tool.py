from toscatranslator.configuration_tools.common.configuration_tool import *
from toscatranslator.common.tosca_reserved_keys import PARAMETERS, VALUE, EXTRA, SOURCE, GET_OPERATION_OUTPUT, INPUTS, \
    NODE_FILTER, NAME
from toscatranslator.common import snake_case
from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.common.exception import ProviderConfigurationParameterError

import copy, yaml, os, itertools

REGISTER = 'register'
DEFAULT_HOST = 'localhost'
SET_FACT_MODULE = 'set_fact'
IMPORT_TASKS_MODULE = 'include'

ARTIFACTS_DIRECTORY = 'artifacts'


class AnsibleConfigurationTool(ConfigurationTool):
    """
    Must be tested by TestAnsibleOpenstack.test_translating_to_ansible
    """

    def to_dsl_for_create(self, provider, nodes_relationships_queue, artifacts, target_directory):
        self.target_directory = target_directory
        self.provider_config = ProviderConfiguration(provider)
        self.artifacts = {}
        for art in artifacts:
            self.artifacts[art[NAME]] = art

        for v in nodes_relationships_queue:
            self.gather_global_operations(v)

        for op_name, op in self.global_operations_info.items():
            self.global_operations_info[op_name] = self.replace_all_get_functions(op)

        elements_queue = []
        for v in nodes_relationships_queue:
            (_, element_type, _) = tosca_type.parse(v.type)
            if element_type == NODES:
                new_conf_args = self.replace_all_get_functions(v.configuration_args)
                v.configuration_args = new_conf_args
                elements_queue.append(v)

        ansible_task_list = []
        for v in self.global_operations_queue:
            ansible_task_list.extend(self.get_ansible_tasks_from_operation(v))

        for v in elements_queue:
            ansible_task_list.extend(self.get_ansible_tasks_for_create(v))

        ansible_playbook = [dict(
            name='Create ' + provider + ' cluster',
            hosts=DEFAULT_HOST,
            tasks=ansible_task_list
        )]

        return ansible_playbook

    def replace_all_get_functions(self, data):
        if isinstance(data, dict):
            if len(data) == 1:
                if next(iter(data.keys())) == GET_OPERATION_OUTPUT:
                    full_op_name = '_'.join(data[GET_OPERATION_OUTPUT][:3]).lower()
                    output_id = self.global_operations_info[full_op_name][OUTPUT_IDS][data[GET_OPERATION_OUTPUT][-1]]
                    return self.rap_ansible_variable(output_id)

            r = {}
            for k, v in data.items():
                r[k] = self.replace_all_get_functions(v)
            return r

        elif isinstance(data, (list, set, tuple)):
            type_save = type(data)
            r = type_save()
            for i in data:
                temp = self.replace_all_get_functions(i)
                r = type_save(itertools.chain(r, [temp]))
            return r
        else:
            return data

    def get_ansible_tasks_for_create(self, element_object, additional_args=None):
        """
        Fulfill the dict with ansible task arguments to create infrastructure
        If the node contains get_operation_output parameters then the operation is executed
        If the operation is not mentioned then it is not executed
        Operations are mentioned in the node or in relationship_template
        :param: node: ProviderResource
        :param additional_args: dict of arguments to add
        :return: string of ansible task to place in playbook
        """

        if additional_args is None:
            additional_args = {}

        ansible_tasks_for_create = []

        config = self.provider_config.get_subsection('ansible', 'node_filter')
        if not config:
            config = {}
        node_filter_source_prefix = config.get('node_filter_source_prefix', '')
        node_filter_source_postfix = config.get('node_filter_source_postfix', '')
        node_filter_exceptions = config.get('node_filter_exceptions', '')
        node_filter_inner_variable = config.get('node_filter_inner_variable')

        configuration_args = {}
        for arg_key, arg in element_object.configuration_args.items():
            if isinstance(arg, dict):
                node_filter_key = arg.get(SOURCE, {}).get(NODE_FILTER)
                node_filter_value = arg.get(VALUE)
                node_filter_params = arg.get(PARAMETERS)

                if node_filter_key and node_filter_value and node_filter_params:
                    node_filter_source = node_filter_source_prefix + node_filter_key + node_filter_source_postfix
                    if node_filter_exceptions.get(node_filter_key):
                        node_filter_source = node_filter_exceptions[node_filter_key]

                    seed(time())
                    node_filter_value_with_id = node_filter_value + '_' + str(randint(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))

                    NODE_FILTER_FACTS = 'node_filter_facts'
                    NODE_FILTER_FACTS_REGISTER = NODE_FILTER_FACTS + '_raw'
                    NODE_FILTER_FACTS_VALUE = NODE_FILTER_FACTS_REGISTER
                    if node_filter_inner_variable:
                        if isinstance(node_filter_inner_variable, dict):
                            node_filter_inner_variable = node_filter_inner_variable.get(node_filter_key, '')
                        if isinstance(node_filter_inner_variable, six.string_types):
                            node_filter_inner_variable = [node_filter_inner_variable]
                        if isinstance(node_filter_inner_variable, list):
                            for v in node_filter_inner_variable:
                                NODE_FILTER_FACTS_VALUE += '[\"' + v + '\"]'
                        else:
                            ExceptionCollector.appendException(ProviderConfigurationParameterError(
                                what='ansible.node_filter: node_filter_inner_variable'
                            ))

                    include_path = self.copy_condition_to_the_directory('equals', self.target_directory)
                    ansible_tasks = [
                        {
                            node_filter_source: {},
                            REGISTER: NODE_FILTER_FACTS_REGISTER
                        },
                        {
                            SET_FACT_MODULE: {
                                "input_facts": self.rap_ansible_variable(NODE_FILTER_FACTS_VALUE)
                            }
                        },
                        {
                            SET_FACT_MODULE: {
                                "input_args": node_filter_params
                            }
                        },
                        {
                            IMPORT_TASKS_MODULE: include_path
                        },
                        {
                            SET_FACT_MODULE: {
                                node_filter_value_with_id: self.rap_ansible_variable('matched_object[\"' + node_filter_value + '\"]')
                            }
                        }
                    ]
                    # self.copy_conditions_to_the_directory({'equals'}, self.target_directory)
                    ansible_tasks_for_create.extend(ansible_tasks)
                    arg = self.rap_ansible_variable(node_filter_value_with_id)
            configuration_args[arg_key] = arg

        ansible_args = copy.copy(element_object.configuration_args)
        ansible_args['state'] = 'present'
        ansible_task_as_dict = dict()
        ansible_task_as_dict['name'] = self.ansible_description_by_type(element_object)
        ansible_task_as_dict[self.ansible_module_by_type(element_object)] = configuration_args
        ansible_tasks_for_create.append(ansible_task_as_dict)

        return ansible_tasks_for_create

    def ansible_description_by_type(self, provider_source_obj):
        module_desc = 'Create element'
        ansible_config = self.provider_config.get_section('ansible')
        if ansible_config:
            new_module_desc = ansible_config.get('module_description')
            if new_module_desc:
                module_desc = new_module_desc
        return module_desc + ' ' + snake_case.convert(provider_source_obj.type_name).replace('_', ' ')

    def ansible_module_by_type(self, provider_source_obj):
        module_prefix = ''
        ansible_config = self.provider_config.get_section('ansible')
        if ansible_config:
            new_module_prefix = self.provider_config.config['ansible'].get('module_prefix')
            if new_module_prefix:
                module_prefix = new_module_prefix
        return module_prefix + snake_case.convert(provider_source_obj.type_name)

    def get_ansible_tasks_from_operation(self, op_name):
        tasks = []

        op_info = self.global_operations_info[op_name]
        if not op_info.get(OUTPUT_IDS) or not op_info.get(IMPLEMENTATION):
            return []

        import_task_arg = op_info[IMPLEMENTATION]
        if not isinstance(import_task_arg, list):
            import_task_arg = [import_task_arg]

        if op_info.get(INPUTS):
            for k, v in op_info[INPUTS].items():
                arg_v = v

                if isinstance(v, (dict, list, set, tuple)):
                    seed(time())
                    arg_v = '_'.join([k, str(randint(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))])
                    new_task = {
                        SET_FACT_MODULE: {
                            arg_v: v
                        }
                    }
                    tasks.append(new_task)
                    arg_v = self.rap_ansible_variable(arg_v)
                arg_k = k
                new_task = {
                    SET_FACT_MODULE: {
                        arg_k: arg_v
                    }
                }
                tasks.append(new_task)
        for i in import_task_arg:
            if self.artifacts.get(i):
                art_data = self.artifacts[i]
                new_tasks = self.create_artifact_data(art_data)
                tasks.extend(new_tasks)
            else:
                abs_path_file = os.path.abspath(os.path.join(self.target_directory, i))
                new_task = {
                    IMPORT_TASKS_MODULE: abs_path_file
                }
                tasks.append(new_task)
        for k, v in op_info[OUTPUT_IDS].items():
            new_task = {
                SET_FACT_MODULE: {
                    v: self.rap_ansible_variable(k)
                }
            }
            tasks.append(new_task)
        return tasks

    def rap_ansible_variable(self, s):
        r = "{{ " + s + " }}"
        return r

    @staticmethod
    def create_artifact_data(data):
        parameters = data[PARAMETERS]
        source = data[SOURCE]
        extra = data.get(EXTRA)
        value = data[VALUE]
        task_data = {
            source: parameters,
            REGISTER: value
        }
        tasks = [
            task_data
        ]
        if extra:
            task_data.update(extra)
        return tasks

    def create_artifact(self, filename, data):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        tasks = AnsibleConfigurationTool.create_artifact_data(data)
        with open(filename, "w") as f:
            filedata = yaml.dump(tasks)
            f.write(filedata)

        return

    def copy_condition_to_the_directory(self, cond, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), ARTIFACTS_DIRECTORY)
        filename = os.path.join(tool_artifacts_dir, cond + '.yaml')
        if not os.path.isfile(filename):
            ExceptionCollector.appendException(ConditionFileError(
                what=filename
            ))
        target_filename = os.path.join(target_directory, cond + '.yaml')
        copyfile(filename, target_filename)
        return os.path.abspath(target_filename)

    def copy_conditions_to_the_directory(self, conditions_set, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), ARTIFACTS_DIRECTORY)
        for cond in conditions_set:
            filename = os.path.join(tool_artifacts_dir, cond + '.yaml')
            if not os.path.isfile(filename):
                ExceptionCollector.appendException(ConditionFileError(
                    what=filename
                ))
            target_filename = os.path.join(target_directory, cond + '.yaml')
            copyfile(filename, target_filename)