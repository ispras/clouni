from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import PARAMETERS, VALUE, EXTRA, SOURCE, INPUTS, NODE_FILTER, NAME, \
    NODES, GET_OPERATION_OUTPUT, IMPLEMENTATION, ANSIBLE, GET_INPUT

from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.configuration_tools.common.configuration_tool import ConfigurationTool, \
    OUTPUT_IDS, OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END

import copy, sys, yaml, os, itertools, six, logging
from shutil import copyfile

ANSIBLE_RESERVED_KEYS = \
    (REGISTER, PATH, FILE, STATE, LINEINFILE, SET_FACT, IS_DEFINED, IS_UNDEFINED, IMPORT_TASKS_MODULE) = \
    ('register', 'path', 'file', 'state', 'lineinfile', 'set_fact', ' is defined', 'is_undefined', 'include')

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
                logging.error("Configuration parameter \'%s\' is missing in Ansible configuration" % param)
                sys.exit(1)

        for param in REQUIRED_CONFIG_PARAMS:
            setattr(self, param, main_config[param])

    def to_dsl(self, provider, nodes_relationships_queue, cluster_name, is_delete, artifacts=None,
               target_directory=None, inputs=None, outputs=None, extra=None):

        if artifacts is None:
            artifacts = []
        if target_directory is None:
            target_directory = self.initial_artifacts_directory

        self.artifacts = {}
        for art in artifacts:
            self.artifacts[art[NAME]] = art

        provider_config = ProviderConfiguration(provider)
        ansible_config = provider_config.get_section(ANSIBLE)
        node_filter_config = provider_config.get_subsection(ANSIBLE, NODE_FILTER)
        provider_async_default_delay = ansible_config.get(ASYNC_DEFAULT_DELAY) or \
                                       self.async_default_delay
        provider_async_default_retries = ansible_config.get(ASYNC_DEFAULT_RETRIES) or \
                                         self.async_default_retries
        provider_async_default_time = ansible_config.get(ASYNC_DEFAULT_TIME) or self.async_default_time
        extra_async = self.get_extra_async(extra, provider_async_default_time)

        prev_dep_order = 0
        ids_file_path = self.rap_ansible_variable("playbook_dir") + '/id_vars_' + cluster_name + self.get_artifact_extension()
        self.init_global_variables(inputs)
        elements_queue, software_queue = self.init_queue(nodes_relationships_queue)
        ansible_task_list = self.get_ansible_tasks_for_inputs(inputs)
        ansible_post_task_list = []
        host_list = []

        if not is_delete:
            for v in self.global_operations_queue:
                ansible_task_list.extend(self.get_ansible_tasks_from_operation(v, target_directory))

            ansible_task_list.append({FILE: {
                PATH: ids_file_path,
                STATE: 'absent'}})
            ansible_task_list.append({FILE: {
                PATH: ids_file_path,
                STATE: 'touch'}})
        else:
            elements_queue.reverse()
            ansible_task_list.append({'include_vars': ids_file_path})

        check_async_tasks = []

        for v in elements_queue:
            extra_tasks_for_delete = self.get_extra_tasks_for_delete(v.name.replace('-', '_'), ids_file_path)
            description_prefix, module_prefix = self.get_module_prefixes(is_delete, ansible_config)
            description_by_type = self.ansible_description_by_type(v.type_name, description_prefix)
            module_by_type = self.ansible_module_by_type(v.type_name, module_prefix)
            ansible_tasks = self.get_ansible_tasks_from_interface(v, target_directory, is_delete,
                                                            additional_args=extra)
            if len(ansible_tasks) == 0:
                if not is_delete:
                    ansible_tasks, post_tasks, host = self.get_ansible_tasks_for_create(v, target_directory, node_filter_config,
                                                                      description_by_type, module_by_type,
                                                                      additional_args=extra)
                else:
                    ansible_tasks = self.get_ansible_tasks_for_delete(v, description_by_type, module_by_type,
                                                                      additional_args=extra)
            tasks_for_async = self.get_ansible_tasks_for_async(v, description_prefix, provider_async_default_retries,
                                                               provider_async_default_delay)
            if not is_delete or is_delete and not any(item == module_by_type for item in
                                     ansible_config.get('modules_skipping_delete', [])):
                if extra_async != False:
                    if prev_dep_order != v.dependency_order:
                        ansible_task_list.extend(check_async_tasks)
                        check_async_tasks = []
                        prev_dep_order = v.dependency_order
                    check_async_tasks.extend(tasks_for_async)
                ansible_task_list.extend(ansible_tasks)
                if not is_delete:
                    if 'name' in host and post_tasks != []:
                        ansible_post_task_list.append(post_tasks)
                        host_list.append(host['name'])

            if not is_delete:
                if extra_async != False:
                    check_async_tasks.extend(extra_tasks_for_delete)
                else:
                    ansible_task_list.extend(extra_tasks_for_delete)

        if extra_async != False:
            ansible_task_list.extend(check_async_tasks)

        if is_delete:
            ansible_task_list.append({FILE: {
                PATH: ids_file_path,
                STATE: 'absent'}})

        ansible_playbook = [dict(
            name=description_prefix + ' ' + provider + ' cluster',
            hosts=self.default_host,
            tasks=ansible_task_list
        )]

        for v in software_queue:
            ansible_tasks = self.get_ansible_tasks_from_interface(v, target_directory, is_delete,
                                                                  additional_args=extra)
            software_playbook = dict(
                name=description_prefix + ' ' + v.name + ' ' + ' software component',
                hosts=v.host,
                tasks=ansible_tasks
            )
            ansible_playbook.append(software_playbook)

        if ansible_post_task_list is not None:
            for i in range(len(host_list)):
                configure_playbook = dict(
                    name=description_prefix + ' ' + v.name + ' ' + 'server component',
                    hosts=host_list[i],
                    tasks=ansible_post_task_list[i]
                )
                ansible_playbook.append(configure_playbook)


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

    def init_queue(self, nodes_relationships_queue):
        elements_queue = []
        software_queue = []
        for v in nodes_relationships_queue:
            self.gather_global_operations(v)
        #print(self.global_operations_info.items())
        for op_name, op in self.global_operations_info.items():
            self.global_operations_info[op_name] = self.replace_all_get_functions(op)
        for v in nodes_relationships_queue:
            (_, element_type, _) = utils.tosca_type_parse(v.type)
            if element_type == NODES:
                new_conf_args = self.replace_all_get_functions(v.configuration_args)
                v.configuration_args = new_conf_args
                if v.is_software_component:
                    software_queue.append(v)
                else:
                    elements_queue.append(v)
        return elements_queue, software_queue

    def replace_all_get_functions(self, data):
        if isinstance(data, dict):
            if len(data) == 1 and next(iter(data.keys())) == GET_OPERATION_OUTPUT:
                full_op_name = '_'.join(data[GET_OPERATION_OUTPUT][:3]).lower()
                output_id = self.global_operations_info[full_op_name][OUTPUT_IDS][data[GET_OPERATION_OUTPUT][-1]]
                return self.rap_ansible_variable(output_id)
            if len(data) == 1 and next(iter(data.keys())) == GET_INPUT:
                output_id = self.global_variables['input_'+data[GET_INPUT]]
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

    def get_ansible_tasks_for_create(self, element_object, target_directory, node_filter_config, description_by_type,
                                     module_by_type, additional_args=None):
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

        ansible_tasks = []
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
                            logging.error("Provider configuration parameter "
                                          "\'ansible.node_filter: node_filter_inner_variable\' is missing "
                                          "or has unsupported value \'%s\'" % node_filter_inner_variable)
                            sys.exit(1)

                    include_path = self.copy_condition_to_the_directory('equals', target_directory)
                    ansible_tasks_temp = [
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
                    ansible_tasks.extend(ansible_tasks_temp)
                    arg = self.rap_ansible_variable(node_filter_value_with_id)
            configuration_args[arg_key] = arg

        post_tasks = []
        for i in element_object.nodetemplate.interfaces:
            if i.name == 'preconfigure':
                op_name = '_'.join([element_object.name, i.interfacetype.split('.')[::-1][0].lower() , 'preconfigure'])
                if not self.global_operations_info.get(op_name, {}).get(OUTPUT_IDS):
                    ansible_tasks.extend(
                        self.get_ansible_tasks_from_operation(op_name, target_directory, True))
            if i.name == 'configure':
                op_name = '_'.join([element_object.name, i.interfacetype.split('.')[::-1][0].lower(), 'configure'])
                if not self.global_operations_info.get(op_name, {}).get(OUTPUT_IDS):
                    post_tasks.extend(
                        self.get_ansible_tasks_from_operation(op_name, target_directory, True))
        ansible_args = copy.copy(element_object.configuration_args)
        ansible_args[STATE] = 'present'
        task_name = element_object.name.replace('-', '_')
        ansible_task_as_dict = dict()
        ansible_task_as_dict[NAME] = description_by_type
        ansible_task_as_dict[module_by_type] = configuration_args
        ansible_task_as_dict[REGISTER] = task_name
        ansible_task_as_dict.update(additional_args)
        ansible_tasks.append(ansible_task_as_dict)
        #ansible_tasks.extend(post_tasks)
        return ansible_tasks, post_tasks, configuration_args

    def get_ansible_tasks_for_delete(self, element_object, description_by_type, module_by_type, additional_args=None):
        """
        Fulfill the dict with ansible task arguments to delete infrastructure
        Operations are mentioned in the node or in relationship_template
        :param: node: ProviderResource
        :return: string of ansible task to place in playbook
        """
        ansible_tasks = []
        if additional_args is None:
            additional_args = {}
        else:
            additional_args_global = copy.deepcopy(additional_args.get('global', {}))
            additional_args_element = {}
            additional_args = utils.deep_update_dict(additional_args_global, additional_args_element)

        task_name = element_object.name.replace('-', '_')
        ansible_task_list = [dict(), dict()]
        for task in ansible_task_list:
            task[NAME] = description_by_type
        ansible_task_list[0][module_by_type] = {
            NAME: self.rap_ansible_variable(task_name + '_delete'), 'state': 'absent'}
        ansible_task_list[1][module_by_type] = {
            NAME: self.rap_ansible_variable('item'), 'state': 'absent'}
        ansible_task_list[0]['when'] = task_name + '_delete' + IS_DEFINED
        ansible_task_list[1]['when'] = task_name + '_ids is defined'
        ansible_task_list[1]['loop'] = self.rap_ansible_variable(task_name + '_ids | flatten(levels=1)')
        for task in ansible_task_list:
            task[REGISTER] = task_name + '_var'
            task.update(additional_args)
            ansible_tasks.append(task)
            ansible_tasks.append(
                {SET_FACT: task_name + '=\'' + self.rap_ansible_variable(task_name + '_var') + '\'',
                 'when': task_name + '_var' + '.changed'})
        return ansible_tasks

    def get_ansible_tasks_from_interface(self, element_object, target_directory, is_delete, additional_args=None):
        if additional_args is None:
            additional_args = {}
        else:
            additional_args_global = copy.deepcopy(additional_args.get('global', {}))
            additional_args_element = copy.deepcopy(additional_args.get(element_object.name, {}))
            additional_args = utils.deep_update_dict(additional_args_global,
                                                     additional_args_element)
        ansible_tasks = []
        scripts = []
        for interface in element_object.nodetemplate.interfaces:
            if not is_delete and interface.name == 'create' or is_delete and interface.name == 'delete':
                #if not is_delete and interface.name == 'create' or is_delete and interface.name == 'delete' or interface.name == 'configure' and interface.type == 'Standard':
                implementations = interface.implementation
                if isinstance(interface.implementation, six.string_types):
                    implementations = [interface.implementation]
                scripts.extend(implementations)
                for script in implementations:
                    import_file = os.path.join(target_directory, os.path.basename(script))
                    os.makedirs(os.path.dirname(import_file), exist_ok=True)
                    copyfile(script, import_file)
                    if interface.inputs is not None:
                        for input_name, input_value in interface.inputs.items():
                            ansible_tasks.append({
                                SET_FACT: {
                                    input_name: input_value
                                }
                            })
                    new_ansible_task = {
                        IMPORT_TASKS_MODULE: import_file
                    }
                    new_ansible_task.update(additional_args)
                    ansible_tasks.append(new_ansible_task)

        return ansible_tasks

    def ansible_description_by_type(self, provider_source_obj_type, description_prefix):
        return description_prefix + ' ' + utils.snake_case(provider_source_obj_type).replace('_', ' ')

    def ansible_module_by_type(self, provider_source_obj_type, module_prefix):
        return module_prefix + utils.snake_case(provider_source_obj_type)

    def get_module_prefixes(self, is_delete, ansible_config=None, low=False):
        if is_delete:
            desc = 'Delete'
        else:
            desc = 'Create'
        module_prefix = ''
        if ansible_config:
            new_module_desc = ansible_config.get('module_description' + '_' + desc.lower())
            if new_module_desc:
                desc = new_module_desc
            new_module_prefix = ansible_config.get('module_prefix')
            if new_module_prefix:
                module_prefix = new_module_prefix
        if low:
            desc = desc.lower()
        return desc, module_prefix

    def get_ansible_tasks_from_operation(self, op_name, target_directory, if_required=False):
        tasks = []
        #print(self.global_operations_info[op_name])
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
                new_task = {
                    IMPORT_TASKS_MODULE: os.path.join(target_directory, i)
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
        logging.debug("New artifact was created: \n%s" % yaml.dump(tasks))
        return tasks

    def create_artifact(self, filename, data):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        tasks = AnsibleConfigurationTool.create_artifact_data(data)
        with open(filename, "w") as f:
            filedata = yaml.dump(tasks, default_flow_style=False, sort_keys=False)
            f.write(filedata)
            logging.info("Artifact for executor %s was created: %s" % (self.TOOL_NAME, filename))

    def copy_condition_to_the_directory(self, cond, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.initial_artifacts_directory)
        filename = os.path.join(tool_artifacts_dir, cond + self.get_artifact_extension())
        if not os.path.isfile(filename):
            logging.error("File containing condition \'%s\' not found in \'%s\'" % (cond, filename))
            sys.exit(1)
        target_filename = os.path.join(target_directory, cond + self.get_artifact_extension())
        copyfile(filename, target_filename)
        return target_filename

    def copy_conditions_to_the_directory(self, conditions_set, target_directory):
        os.makedirs(target_directory, exist_ok=True)
        tool_artifacts_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.initial_artifacts_directory)
        for cond in conditions_set:
            filename = os.path.join(tool_artifacts_dir, cond + self.get_artifact_extension())
            if not os.path.isfile(filename):
                logging.error("Error loading condition file \'%s\'" % filename)
            else:
                target_filename = os.path.join(target_directory, cond + self.get_artifact_extension())
                copyfile(filename, target_filename)
                logging.info("File \'%s\' was successfully copied to the directory \'%s\'" % (filename, target_directory))

    def get_ansible_tasks_for_async(self, element_object, description_prefix, retries=None, delay=None):
        jid = '.'.join([element_object.name, 'ansible_job_id'])
        results_var = '.'.join([element_object.name, 'results'])
        tasks = [
            {
                NAME: 'Checking ' + element_object.name + ' ' + description_prefix.lower() + 'd',
                'async_status': 'jid=' + self.rap_ansible_variable(jid),
                REGISTER: 'async_result_status',
                'until': 'async_result_status.finished',
                'retries': retries,
                'delay': delay,
                'when': jid + IS_DEFINED
            },
            {
                NAME: 'Checking ' + element_object.name + ' ' + description_prefix.lower() + 'd',
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

    def init_global_variables(self, inputs):
        if inputs == None:
            return
        for input in inputs:
            self.global_variables['input_' + input.name] = \
                input.name + '_' + str(utils.get_random_int(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))
        return

    def get_ansible_tasks_for_inputs(self, inputs):
        ansible_tasks = []
        for input in inputs:
            if input.default != None:
                ansible_tasks.append({
                    SET_FACT: {
                        input.name: input.default
                    },
                    'when': input.name + IS_UNDEFINED
                })
            ansible_tasks.append({
                SET_FACT: {
                    self.global_variables['input_' + input.name]: self.rap_ansible_variable(input.name)
                }
            })
        return ansible_tasks
