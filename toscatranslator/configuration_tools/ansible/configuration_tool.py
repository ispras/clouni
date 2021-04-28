import copy
import yaml
import os
import itertools
import six
from shutil import copyfile

from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import ProviderConfigurationParameterError, ConditionFileError, \
    ConfigurationParameterError

from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import PARAMETERS, VALUE, EXTRA, SOURCE, INPUTS, NODE_FILTER, NAME, \
    NODES, GET_OPERATION_OUTPUT, IMPLEMENTATION, ANSIBLE

from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.configuration_tools.common.configuration_tool import ConfigurationTool, \
    OUTPUT_IDS, OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END

ANSIBLE_RESERVED_KEYS = (REGISTER, PATH, FILE, STATE, LINEINFILE, SET_FACT, IS_DEFINED, IMPORT_TASKS_MODULE) = \
    ('register', 'path', 'file', 'state', 'lineinfile', 'set_fact', ' is defined', 'include')

REQUIRED_CONFIG_PARAMS = (ASYNC_DEFAULT_TIME, ASYNC_DEFAULT_RETRIES, ASYNC_DEFAULT_DELAY, INITIAL_ARTIFACTS_DIRECTORY,
                       DEFAULT_HOST) = ("async_default_time", "async_default_retries", "async_default_delay",
                                        "initial_artifacts_directory", "default_host")


class AnsibleConfigurationTool(ConfigurationTool):
    TOOL_NAME = ANSIBLE
    """
    Must be tested by TestAnsibleOpenstack.test_translating_to_ansible
    """

    def __init__(self):
        super(AnsibleConfigurationTool, self).__init__()

        main_config = self.tool_config.get_section('main')
        for param in REQUIRED_CONFIG_PARAMS:
            if not param in main_config.keys():
                raise ConfigurationParameterError()

        for param in REQUIRED_CONFIG_PARAMS:
            setattr(self, param, main_config[param])

    def to_dsl_for_create(self, provider, nodes_relationships_queue, artifacts, target_directory, cluster_name,
                          extra=None):
        provider_config = ProviderConfiguration(provider)
        ansible_config = provider_config.get_section(ANSIBLE)
        provider_async_default_delay = ansible_config.get(ASYNC_DEFAULT_DELAY) or \
                                       self.async_default_delay
        provider_async_default_retries = ansible_config.get(ASYNC_DEFAULT_RETRIES) or \
                                         self.async_default_retries
        provider_async_default_time = ansible_config.get(ASYNC_DEFAULT_TIME) or self.async_default_time

        extra_async = self.get_extra_async(extra, provider_async_default_time)
        prev_dep_order = 0

        path = self.rap_ansible_variable("playbook_dir") + '/id_vars_' + cluster_name + self.get_artifact_extension()

        self.__description = 'Create'
        self.artifacts = {}
        for art in artifacts:
            self.artifacts[art[NAME]] = art
        elements_queue = self.init_queue(nodes_relationships_queue)

        ansible_task_list = []
        for v in self.global_operations_queue:
            ansible_task_list.extend(self.get_ansible_tasks_from_operation(v, target_directory))

        ansible_task_list.append({FILE: {
            PATH: path,
            STATE: 'absent'}})
        ansible_task_list.append({FILE: {
            PATH: path,
            STATE: 'touch'}})

        check_async_tasks = []
        for v in elements_queue:
            if extra_async != False:
                check_async_tasks, ansible_task_list, prev_dep_order = self.add_async_task(v, v.dependency_order, check_async_tasks, ansible_task_list, prev_dep_order, provider_async_default_retries, provider_async_default_delay)
            if extra_async != False:
                check_async_tasks.extend(self.get_extra_tasks_for_delete(v.name.replace('-', '_'), path))
            ansible_task_list.extend(
                self.get_ansible_tasks_for_create(v, target_directory, provider_config, additional_args=extra))
            if extra_async == False:
                ansible_task_list.extend(self.get_extra_tasks_for_delete(v.name.replace('-', '_'), path))
        if extra_async != False:
            ansible_task_list.extend(check_async_tasks)

        ansible_playbook = [dict(
            name=self.__description + ' ' + provider + ' cluster',
            hosts=self.default_host,
            tasks=ansible_task_list
        )]
        return yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False)

    def to_dsl_for_delete(self, provider, nodes_relationships_queue, cluster_name, extra=None):
        ansible_config = ProviderConfiguration(provider).get_section(ANSIBLE)
        provider_async_default_delay = ansible_config.get(ASYNC_DEFAULT_DELAY) or \
                                       self.async_default_delay
        provider_async_default_retries = ansible_config.get(ASYNC_DEFAULT_RETRIES) or \
                                         self.async_default_retries
        provider_async_default_time = ansible_config.get(ASYNC_DEFAULT_TIME) or self.async_default_time

        extra_async = self.get_extra_async(extra, provider_async_default_time)

        path = self.rap_ansible_variable("playbook_dir") + '/id_vars_' + cluster_name + self.get_artifact_extension()
        prev_dep_order = 0

        self.__description = 'Delete'
        elements_queue = self.init_queue(nodes_relationships_queue)

        ansible_task_list = []
        elements_queue.reverse()
        ansible_task_list.append({'include_vars': path})


        check_async_tasks = []
        for v in elements_queue:
            if not any(item == self.ansible_module_by_type(v, ansible_config) for item in
                       ansible_config.get('modules_skipping_delete', [])):
                if extra_async != False:
                    check_async_tasks, ansible_task_list, prev_dep_order = self.add_async_task(v, v.dependency_order, check_async_tasks, ansible_task_list, prev_dep_order, provider_async_default_delay, provider_async_default_retries)
                ansible_task_list.extend(self.get_ansible_tasks_for_delete(v, ansible_config, additional_args=extra))
        if extra_async != False:
            ansible_task_list.extend(check_async_tasks)

        ansible_task_list.append({FILE: {
            PATH: path,
            STATE: 'absent'}})
        ansible_playbook = [dict(
            name=self.__description + ' ' + provider + ' cluster',
            hosts=self.default_host,
            tasks=ansible_task_list
        )]

        return yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False)

    def get_extra_async(self, extra, async_default_time):
        """
        Check if deploy asynchronously
        :param extra: extra passed by user
        :param async_default_time: parameter from config
        :return: False or integer which equals async default time
        """
        if not extra:
            extra = dict()
        extra_async = extra.get('global', {}).get('async', False)
        if extra_async == True:
            extra_async = int(async_default_time)
        return extra_async

    def add_async_task(self, v, dependency_order, check_async_tasks, ansible_task_list, prev_dep_order, retries, delay):
        if prev_dep_order != dependency_order:
            ansible_task_list.extend(check_async_tasks)
            check_async_tasks = []
            prev_dep_order = dependency_order
        check_async_tasks.extend(self.get_ansible_tasks_for_async(v, retries, delay))
        return check_async_tasks, ansible_task_list, prev_dep_order

    def init_queue(self, nodes_relationships_queue):
        elements_queue = []
        for v in nodes_relationships_queue:
            self.gather_global_operations(v)
        for op_name, op in self.global_operations_info.items():
            self.global_operations_info[op_name] = self.replace_all_get_functions(op)
        for v in nodes_relationships_queue:
            (_, element_type, _) = utils.tosca_type_parse(v.type)
            if element_type == NODES:
                new_conf_args = self.replace_all_get_functions(v.configuration_args)
                v.configuration_args = new_conf_args
                elements_queue.append(v)
        return elements_queue

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

    def get_ansible_tasks_for_create(self, element_object, target_directory, config, additional_args=None):
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

        node_filter_config = config.get_subsection(ANSIBLE, NODE_FILTER)
        if not node_filter_config:
            node_filter_config = {}
        node_filter_source_prefix = node_filter_config.get('node_filter_source_prefix', '')
        node_filter_source_postfix = node_filter_config.get('node_filter_source_postfix', '')
        node_filter_exceptions = node_filter_config.get('node_filter_exceptions', '')
        node_filter_inner_variable = node_filter_config.get('node_filter_inner_variable')

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

                    node_filter_value_with_id = node_filter_value + '_' + str(
                        utils.get_random_int(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))

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

                    include_path = self.copy_condition_to_the_directory('equals', target_directory)
                    ansible_tasks = [
                        {
                            node_filter_source: {},
                            REGISTER: NODE_FILTER_FACTS_REGISTER
                        },
                        {
                            SET_FACT: {
                                "input_facts": self.rap_ansible_variable(NODE_FILTER_FACTS_VALUE)
                            }
                        },
                        {
                            SET_FACT: {
                                "input_args": node_filter_params
                            }
                        },
                        {
                            IMPORT_TASKS_MODULE: include_path
                        },
                        {
                            SET_FACT: {
                                node_filter_value_with_id: self.rap_ansible_variable(
                                    'matched_object[\"' + node_filter_value + '\"]')
                            }
                        }
                    ]
                    # self.copy_conditions_to_the_directory({'equals'}, target_directory)
                    ansible_tasks_for_create.extend(ansible_tasks)
                    arg = self.rap_ansible_variable(node_filter_value_with_id)
            configuration_args[arg_key] = arg

        for i in element_object.nodetemplate.interfaces:
            if i.name == 'preconfigure':
                op_name = '_'.join([element_object.name, 'prepare', 'preconfigure'])
                if not self.global_operations_info.get(op_name, {}).get(OUTPUT_IDS):
                    ansible_tasks_for_create.extend(
                        self.get_ansible_tasks_from_operation(op_name, target_directory, True))
        ansible_args = copy.copy(element_object.configuration_args)
        ansible_args[STATE] = 'present'
        task_name = element_object.name.replace('-', '_')
        ansible_task_as_dict = dict()
        ansible_task_as_dict[NAME] = self.ansible_description_by_type(element_object, config.get_section(ANSIBLE))
        ansible_task_as_dict[self.ansible_module_by_type(element_object, config.get_section(ANSIBLE))] = configuration_args
        ansible_task_as_dict[REGISTER] = task_name
        ansible_task_as_dict.update(additional_args)
        ansible_tasks_for_create.append(ansible_task_as_dict)
        return ansible_tasks_for_create

    def get_ansible_tasks_for_delete(self, element_object, ansible_config, additional_args=None):
        """
        Fulfill the dict with ansible task arguments to delete infrastructure
        Operations are mentioned in the node or in relationship_template
        :param: node: ProviderResource
        :return: string of ansible task to place in playbook
        """
        ansible_tasks_for_delete = []
        if additional_args is None:
            additional_args = {}
        else:
            additional_args_global = copy.deepcopy(additional_args.get('global', {}))
            additional_args_element = {}
            additional_args = utils.deep_update_dict(additional_args_global, additional_args_element)

        task_name = element_object.name.replace('-', '_')
        ansible_task_list = [dict(), dict()]
        for task in ansible_task_list: task[NAME] = self.ansible_description_by_type(element_object, ansible_config)
        ansible_task_list[0][self.ansible_module_by_type(element_object, ansible_config)] = {
            NAME: self.rap_ansible_variable(task_name + '_delete'), 'state': 'absent'}
        ansible_task_list[1][self.ansible_module_by_type(element_object, ansible_config)] = {
            NAME: self.rap_ansible_variable('item'), 'state': 'absent'}
        ansible_task_list[0]['when'] = task_name + '_delete' + IS_DEFINED
        ansible_task_list[1]['when'] = task_name + '_ids is defined'
        ansible_task_list[1]['loop'] = self.rap_ansible_variable(task_name + '_ids | flatten(levels=1)')
        for task in ansible_task_list:
            task[REGISTER] = task_name + '_var'
            task.update(additional_args)
            ansible_tasks_for_delete.append(task)
            ansible_tasks_for_delete.append(
                {SET_FACT: task_name + '=\'' + self.rap_ansible_variable(task_name + '_var') + '\'',
                 'when': task_name + '_var' + '.changed'})
        return ansible_tasks_for_delete

    def ansible_description_by_type(self, provider_source_obj, ansible_config):
        module_desc = self.__description + ' element'
        if ansible_config:
            new_module_desc = ansible_config.get('module_description' + '_' + self.__description.lower())
            if new_module_desc:
                module_desc = new_module_desc
        return module_desc + ' ' + utils.snake_case(provider_source_obj.type_name).replace('_', ' ')

    def ansible_module_by_type(self, provider_source_obj, ansible_config):
        module_prefix = ''
        if ansible_config:
            new_module_prefix = ansible_config.get('module_prefix')
            if new_module_prefix:
                module_prefix = new_module_prefix
        return module_prefix + utils.snake_case(provider_source_obj.type_name)

    def get_ansible_tasks_from_operation(self, op_name, target_directory, if_required=False):
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
                    arg_v = '_'.join([k, str(utils.get_random_int(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))])
                    new_task = {
                        SET_FACT: {
                            arg_v: v
                        }
                    }
                    tasks.append(new_task)
                    arg_v = self.rap_ansible_variable(arg_v)
                arg_k = k
                new_task = {
                    SET_FACT: {
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
                abs_path_file = os.path.abspath(os.path.join(target_directory, i))
                new_task = {
                    IMPORT_TASKS_MODULE: abs_path_file
                }
                tasks.append(new_task)
        if op_info.get(OUTPUT_IDS):
            for k, v in op_info[OUTPUT_IDS].items():
                new_task = {
                    SET_FACT: {
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
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.initial_artifacts_directory)
        filename = os.path.join(tool_artifacts_dir, cond + self.get_artifact_extension())
        if not os.path.isfile(filename):
            ExceptionCollector.appendException(ConditionFileError(
                what=filename
            ))
        target_filename = os.path.join(target_directory, cond + self.get_artifact_extension())
        copyfile(filename, target_filename)
        return os.path.abspath(target_filename)

    def copy_conditions_to_the_directory(self, conditions_set, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.initial_artifacts_directory)
        for cond in conditions_set:
            filename = os.path.join(tool_artifacts_dir, cond + self.get_artifact_extension())
            if not os.path.isfile(filename):
                ExceptionCollector.appendException(ConditionFileError(
                    what=filename
                ))
            target_filename = os.path.join(target_directory, cond + self.get_artifact_extension())
            copyfile(filename, target_filename)

    def get_ansible_tasks_for_async(self, element_object, retries=None, delay=None):
        jid = '.'.join([element_object.name, 'ansible_job_id'])
        results_var = '.'.join([element_object.name, 'results'])
        tasks = [
            {
                NAME: 'Checking ' + element_object.name + ' ' + self.__description.lower() + 'd',
                'async_status': 'jid=' + self.rap_ansible_variable(jid),
                REGISTER: 'async_result_status',
                'until': 'async_result_status.finished',
                'retries': retries,
                'delay': delay,
                'when': jid + IS_DEFINED
            },
            {
                NAME: 'Checking ' + element_object.name + ' ' + self.__description.lower() + 'd',
                'async_status': 'jid=' + self.rap_ansible_variable(results_var + '[item|int].ansible_job_id'),
                REGISTER: 'async_result_status_list',
                'until': 'async_result_status_list.finished or async_result_status_list.results[item].finished | default(0)',
                'retries': retries,
                'delay': delay,
                # 'with_items': self.rap_ansible_variable(element_object.name + '.results | default([])'),
                'with_sequence': 'start=0 end=' + self.rap_ansible_variable(results_var + '|length - 1'),
                'when': results_var + IS_DEFINED
            },
            {
                NAME: 'Saving ' + element_object.name + ' result',
                SET_FACT: {
                    element_object.name: self.rap_ansible_variable('async_result_status')
                },
                'when': jid + IS_DEFINED
            },
            {
                NAME: 'Saving ' + element_object.name + ' result',
                SET_FACT: {
                    element_object.name: self.rap_ansible_variable('async_result_status_list')
                },
                'when': results_var + IS_DEFINED
            }
        ]
        return tasks

    def get_extra_tasks_for_delete(self, task_name, path):
        ansible_tasks_for_create = []
        ansible_tasks_for_create.append({
            'set_fact': {
                task_name + '_list': self.rap_ansible_variable(
                    task_name + '_list' + " | default([])") + " + [ \"{{ item.id }}\" ]"},
            'loop': self.rap_ansible_variable(task_name + '.results | flatten(levels=1) '),
            # 'when': task_name + '.results' + IS_DEFINED
            'when': 'item.id ' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            'set_fact': {
                task_name + '_list': {task_name + '_ids': self.rap_ansible_variable(task_name + '_list')}},
            'when': task_name + '_list' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            LINEINFILE: {
                PATH: path,
                'line': '' + task_name + '_delete' + ': ' + self.rap_ansible_variable(task_name + '.id')},
            'when': task_name + '.id' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            LINEINFILE: {
                PATH: path,
                'line': self.rap_ansible_variable(task_name + '_list' + ' | to_nice_yaml')},
            'when': task_name + '_list' + IS_DEFINED
        })
        ansible_tasks_for_create.append({
            'fail': {'msg': 'Variable ' + task_name + ' is undefined! So it will not be deleted'},
            'when': task_name + '_list is undefined and ' + task_name + '.id is undefined',
            'ignore_errors': True})
        return ansible_tasks_for_create

    def get_artifact_extension(self):
        return '.yaml'