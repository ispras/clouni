
from toscatranslator.configuration_tools.common.configuration_tool import *
from toscatranslator.common.tosca_reserved_keys import PARAMETERS, VALUE, EXTRA, SOURCE, GET_OPERATION_OUTPUT, INPUTS, \
    NODE_FILTER, NAME
from toscatranslator.common import snake_case
from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.common.exception import ProviderConfigurationParameterError

import copy, yaml, os, itertools

REGISTER = 'register'
PATH = 'path'
FILE = 'file'
STATE = 'state'
NAME = 'name'
DEFAULT_HOST = 'localhost'
LINEINFILE = 'lineinfile'
SET_FACT_MODULE = 'set_fact'
IMPORT_TASKS_MODULE = 'include'
IS_DEFINED = ' is defined'
ASYNC_DEFAULT_TIME = 60
ASYNC_DEFAULT_TIME_CONFIG_PARAM = 'async_default_time'
ASYNC_DEFAULT_RETRIES_CONFIG_PARAM = 'async_default_retries'
ASYNC_DEFAULT_DELAY_CONFIG_PARAM = 'async_default_delay'
ARTIFACT_EXTENSION = '.yaml'
ARTIFACTS_DIRECTORY = 'artifacts'


class AnsibleConfigurationTool(ConfigurationTool):
    """
    Must be tested by TestAnsibleOpenstack.test_translating_to_ansible
    """
    ARTIFACT_EXTENSION = '.yaml'

    def init(self, provider, artifacts, target_directory, cluster_name, extra=None):
        self.provider_config = ProviderConfiguration(provider)
        self.cluster_name = cluster_name
        self.target_directory = target_directory
        self.path = self.rap_ansible_variable("playbook_dir") + '/id_vars_' + self.cluster_name + ARTIFACT_EXTENSION
        self.artifacts = {}
        for art in artifacts:
            self.artifacts[art[NAME]] = art
        self.extra_async = self.get_extra(extra)
        self.check_async_tasks = []
        self.ansible_task_list = []
        self.prev_dep_order = 0
        self.elements_queue = []

    def get_extra(self, extra):
        if not extra:
            extra = dict()
        extra_async = extra.get('global', {}).get('async', False)
        if extra_async:
            extra_async = int(
                self.provider_config.get_section('ansible').get(ASYNC_DEFAULT_TIME_CONFIG_PARAM, ASYNC_DEFAULT_TIME))
        return extra_async

    def get_async_task(self, v, dependency_order):
        if self.extra_async:
            if self.prev_dep_order < dependency_order:
                self.ansible_task_list.extend(self.check_async_tasks)
                self.check_async_tasks = []
                self.prev_dep_order = dependency_order
            self.check_async_tasks.extend(self.get_ansible_tasks_for_async(v))

    def get_queue(self, nodes_relationships_queue):
        for v in nodes_relationships_queue:
            self.gather_global_operations(v)

        for op_name, op in self.global_operations_info.items():
            self.global_operations_info[op_name] = self.replace_all_get_functions(op)

        for v in nodes_relationships_queue:
            (_, element_type, _) = tosca_type.parse(v.type)
            if element_type == NODES:
                new_conf_args = self.replace_all_get_functions(v.configuration_args)
                v.configuration_args = new_conf_args
                self.elements_queue.append(v)

    def to_dsl_for_create(self, provider, nodes_relationships_queue, artifacts, target_directory, cluster_name,
                          extra=None):
        self.suffix = 'Create'
        self.init(provider, artifacts, target_directory, cluster_name, extra)
        self.get_queue(nodes_relationships_queue)

        for v in self.global_operations_queue:
            self.ansible_task_list.extend(self.get_ansible_tasks_from_operation(v))

        self.ansible_task_list.append({FILE: {
            PATH: self.path,
            STATE: 'absent'}})
        self.ansible_task_list.append({FILE: {
            PATH: self.path,
            STATE: 'touch'}})

        for v in self.elements_queue:
            self.get_async_task(v, v.dependency_order)
            self.ansible_task_list.extend(self.get_ansible_tasks_for_create(v, additional_args=extra))
            if self.extra_async:
                self.ansible_task_list.extend(self.check_async_tasks)
            self.ansible_task_list.extend(self.get_extra_tasks_for_delete(v.name.replace('-', '_')))

        ansible_playbook = [dict(
            name=self.suffix + ' ' + provider + ' cluster',
            hosts=DEFAULT_HOST,
            tasks=self.ansible_task_list
        )]
        return yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False)

    def to_dsl_for_delete(self, provider, nodes_relationships_queue, artifacts, target_directory, cluster_name,
                          extra=None):
        self.init(provider, artifacts, target_directory, cluster_name, extra)
        self.suffix = 'Delete'
        self.get_queue(nodes_relationships_queue)

        self.elements_queue.reverse()
        self.ansible_task_list.append({'include_vars': self.path})
        for v in self.elements_queue:
            self.get_async_task(v, v.dependency_order)
            ansible_config = self.provider_config.get_section('ansible')
            if not any(item == self.ansible_module_by_type(v) for item in
                       ansible_config.get('modules_skipping_delete', [])):
                self.ansible_task_list.extend(self.get_ansible_tasks_for_delete(v))

        if self.extra_async:
            self.ansible_task_list.extend(self.check_async_tasks)
        self.ansible_task_list.append({FILE: {
            PATH: self.path,
            STATE: 'absent'}})
        ansible_playbook = [dict(
            name=self.suffix + ' ' + provider + ' cluster',
            hosts=DEFAULT_HOST,
            tasks=self.ansible_task_list
        )]

        return yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False)

    def replace_all_get_functions(self, data):
        if isinstance(data, dict):
            if len(data) == 1 and next(iter(data.keys())) == GET_OPERATION_OUTPUT:
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
        else:
            additional_args_global = copy.deepcopy(additional_args.get('global', {}))
            additional_args_element = copy.deepcopy(additional_args.get(element_object.name, {}))
            additional_args = utils.deep_update_dict(additional_args_global,
                                                     additional_args_element)

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
                    node_filter_value_with_id = node_filter_value + '_' + str(
                        randint(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))

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
                                node_filter_value_with_id: self.rap_ansible_variable(
                                    'matched_object[\"' + node_filter_value + '\"]')
                            }
                        }
                    ]
                    # self.copy_conditions_to_the_directory({'equals'}, self.target_directory)
                    ansible_tasks_for_create.extend(ansible_tasks)
                    arg = self.rap_ansible_variable(node_filter_value_with_id)
            configuration_args[arg_key] = arg

        for i in element_object.nodetemplate.interfaces:
            if i.name == 'preconfigure':
                op_name = '_'.join([element_object.name, 'prepare', 'preconfigure'])
                if not self.global_operations_info.get(op_name, {}).get(OUTPUT_IDS):
                    ansible_tasks_for_create.extend(self.get_ansible_tasks_from_operation(op_name, True))
        ansible_args = copy.copy(element_object.configuration_args)
        ansible_args[STATE] = 'present'
        task_name = element_object.name.replace('-', '_')
        ansible_task_as_dict = dict()
        ansible_task_as_dict[NAME] = self.ansible_description_by_type(element_object)
        ansible_task_as_dict[self.ansible_module_by_type(element_object)] = configuration_args
        ansible_task_as_dict[REGISTER] = task_name
        ansible_task_as_dict.update(additional_args)
        ansible_tasks_for_create.append(ansible_task_as_dict)
        return ansible_tasks_for_create

    def get_ansible_tasks_for_delete(self, element_object):
        """
        Fulfill the dict with ansible task arguments to delete infrastructure
        Operations are mentioned in the node or in relationship_template
        :param: node: ProviderResource
        :return: string of ansible task to place in playbook
        """
        ansible_tasks_for_delete = []
        task_name = element_object.name.replace('-', '_')
        ansible_task_list = [dict(), dict()]
        ansible_task_list[0][NAME] = self.ansible_description_by_type(element_object)
        ansible_task_list[1][NAME] = self.ansible_description_by_type(element_object)
        ansible_task_list[0][self.ansible_module_by_type(element_object)] = {
            NAME: task_name, 'state': 'absent'}
        ansible_task_list[1][self.ansible_module_by_type(element_object)] = {
            NAME: self.rap_ansible_variable('item'), 'state': 'absent'}
        ansible_task_list[0]['when'] = task_name + IS_DEFINED
        ansible_task_list[1]['when'] = task_name + '_ids is defined'
        ansible_task_list[1]['loop'] = self.rap_ansible_variable(task_name + '_ids | flatten(levels=1)')
        ansible_tasks_for_delete.append(ansible_task_list[0])
        ansible_tasks_for_delete.append(ansible_task_list[1])
        return ansible_tasks_for_delete

    def ansible_description_by_type(self, provider_source_obj):
        module_desc = self.suffix + ' element'
        ansible_config = self.provider_config.get_section('ansible')
        if ansible_config:
            new_module_desc = ansible_config.get('module_description' + '_' + self.suffix.lower())
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

    def get_ansible_tasks_from_operation(self, op_name, if_required=False):
        tasks = []

        op_info = self.global_operations_info[op_name]
        if not if_required and not op_info.get(OUTPUT_IDS) or not op_info.get(IMPLEMENTATION):
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
        if op_info.get(OUTPUT_IDS):
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
            filedata = yaml.dump(tasks, default_flow_style=False, sort_keys=False)
            f.write(filedata)

    def copy_condition_to_the_directory(self, cond, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), ARTIFACTS_DIRECTORY)
        filename = os.path.join(tool_artifacts_dir, cond + ARTIFACT_EXTENSION)
        if not os.path.isfile(filename):
            ExceptionCollector.appendException(ConditionFileError(
                what=filename
            ))
        target_filename = os.path.join(target_directory, cond + ARTIFACT_EXTENSION)
        copyfile(filename, target_filename)
        return os.path.abspath(target_filename)

    def copy_conditions_to_the_directory(self, conditions_set, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), ARTIFACTS_DIRECTORY)
        for cond in conditions_set:
            filename = os.path.join(tool_artifacts_dir, cond + ARTIFACT_EXTENSION)
            if not os.path.isfile(filename):
                ExceptionCollector.appendException(ConditionFileError(
                    what=filename
                ))
            target_filename = os.path.join(target_directory, cond + ARTIFACT_EXTENSION)
            copyfile(filename, target_filename)

    def get_ansible_tasks_for_async(self, element_object):
        config = self.provider_config.get_section('ansible')
        retries = int(config.get(ASYNC_DEFAULT_RETRIES_CONFIG_PARAM, 60))
        delay = int(config.get(ASYNC_DEFAULT_DELAY_CONFIG_PARAM, 5))
        jid = element_object.name + '.ansible_job_id'
        tasks = [
            {
                NAME: 'Checking ' + element_object.name + ' created',
                'async_status': 'jid=' + self.rap_ansible_variable(jid),
                REGISTER: 'create_result_status',
                'until': 'create_result_status.finished',
                'retries': retries,
                'delay': delay,
                'when': jid + IS_DEFINED
            },
            {
                NAME: 'Checking ' + element_object.name + ' created',
                'async_status': 'jid=' + self.rap_ansible_variable('item.ansible_job_id'),
                REGISTER: 'create_result_status',
                'until': 'create_result_status.finished',
                'retries': retries,
                'delay': delay,
                'with_items': self.rap_ansible_variable(element_object.name + '.results | default([])'),
                'when': jid + ' is undefined'
            }
        ]
        return tasks

    def get_extra_tasks_for_delete(self, task_name):
        ansible_tasks_for_create = []
        ansible_tasks_for_create.append({
            'set_fact': {
                task_name + '_list': self.rap_ansible_variable(
                    task_name + '_list' + " | default([])") + " + [ \"{{ item.id }}\" ]"},
            'loop': self.rap_ansible_variable(task_name + '.results | flatten(levels=1) '),
            'when': task_name + '.results' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            'set_fact': {
                task_name + '_list': {task_name + '_ids': self.rap_ansible_variable(task_name + '_list')}},
                'when': task_name + '_list' + IS_DEFINED
            })
        ansible_tasks_for_create.append({
            LINEINFILE: {
                PATH: self.path,
                'line': '' + task_name + ': ' + self.rap_ansible_variable(task_name + '.id')},
            'when': task_name + '.id' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            LINEINFILE: {
                PATH: self.path,
                'line': self.rap_ansible_variable(task_name + '_list' + ' | to_nice_yaml')},
            'when': task_name + '_list' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            'fail': {'msg': 'Variable ' + task_name + ' is undefined! So it will not be deleted'},
            'when': task_name + '_list is undefined and ' + task_name + '.id is undefined',
            'ignore_errors': True})
        return ansible_tasks_for_create