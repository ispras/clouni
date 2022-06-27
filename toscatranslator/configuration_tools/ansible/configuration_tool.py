import time
from multiprocessing import Queue
from random import seed, randint

from graphlib import TopologicalSorter

from toscatranslator.common.tosca_reserved_keys import *
from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import PARAMETERS, VALUE, EXTRA, SOURCE, INPUTS, NODE_FILTER, NAME, \
    NODES, GET_OPERATION_OUTPUT, IMPLEMENTATION, ANSIBLE, GET_INPUT

from toscatranslator.providers.common.provider_configuration import ProviderConfiguration
from toscatranslator.configuration_tools.common.configuration_tool import ConfigurationTool, \
    OUTPUT_IDS, OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END

from toscatranslator.configuration_tools.ansible.runner import run_ansible, parallel_run_ansible, prepare_for_run
from multiprocessing.connection import Listener

import copy, sys, yaml, os, itertools, six, logging
from shutil import copyfile, rmtree


ARTIFACT_RANGE_START = 1000
ARTIFACT_RANGE_END = 9999

ANSIBLE_RESERVED_KEYS = \
    (REGISTER, PATH, FILE, STATE, LINEINFILE, SET_FACT, IS_DEFINED, IS_UNDEFINED, IMPORT_TASKS_MODULE) = \
    ('register', 'path', 'file', 'state', 'lineinfile', 'set_fact', ' is defined', 'is_undefined', 'include')

REQUIRED_CONFIG_PARAMS = (INITIAL_ARTIFACTS_DIRECTORY, DEFAULT_HOST) = ("initial_artifacts_directory", "default_host")
TMP_DIR = '/tmp/clouni'

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

    def to_dsl(self, provider, operations_graph, reversed_operations_graph, cluster_name, is_delete,
               artifacts=None, target_directory=None, inputs=None, outputs=None, extra=None):
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

        ids_file_path = self.rap_ansible_variable(
            "playbook_dir") + '/id_vars_' + cluster_name + self.get_artifact_extension()
        self.init_global_variables(inputs)

        operations_graph = self.init_graph(operations_graph)
        elements = TopologicalSorter(operations_graph)

        if is_delete:
            reversed_operations_graph = self.init_graph(reversed_operations_graph)
            elements = TopologicalSorter(reversed_operations_graph)

        elements.prepare()

        ansible_playbook = []
        self.prepare_for_run()
        q = Queue()
        active = []
        first = True

        while elements.is_active():
            node_name = None
            try:
                node_name = q.get_nowait()
            except:
                time.sleep(1)
            if node_name is not None:
                for node in active:
                    if node.name == node_name:
                        active.remove(node)
                        elements.done(node)
            for v in elements.get_ready():
                if is_delete:
                    v.operations = ['delete']
                logging.debug("Creating ansible play: %s" % v.name)
                extra_tasks_for_delete = self.get_extra_tasks_for_delete(v.name.replace('-', '_'), ids_file_path)
                description_prefix, module_prefix = self.get_module_prefixes(is_delete, ansible_config)
                description_by_type = self.ansible_description_by_type(v.type_name, description_prefix)
                module_by_type = self.ansible_module_by_type(v.type_name, module_prefix)
                ansible_play_for_elem = dict(
                    name=description_prefix + ' ' + provider + ' cluster: ' + v.name,
                    hosts=self.default_host,
                    tasks=[]
                )
                if not is_delete and first:
                    first = False
                    ansible_play_for_elem['tasks'].append(copy.deepcopy({FILE: {
                        PATH: ids_file_path,
                        STATE: 'absent'}}))
                    ansible_play_for_elem['tasks'].append(copy.deepcopy({FILE: {
                        PATH: ids_file_path,
                        STATE: 'touch'}}))
                for op in v.operations:
                    if op == 'delete':
                        # подумать а что если там будет явно задана операция delete в interfaces?
                        if not v.is_software_component:
                            ansible_play_for_elem['tasks'].append(copy.deepcopy({'include_vars': ids_file_path}))
                            ansible_tasks = self.get_ansible_tasks_for_delete(v, description_by_type, module_by_type,
                                                                              additional_args=extra)
                            ansible_tasks.extend(
                                self.get_ansible_tasks_from_interface(v, target_directory, is_delete, op,
                                                                      additional_args=extra))
                            if not any(item == module_by_type for item in
                                       ansible_config.get('modules_skipping_delete', [])):
                                ansible_play_for_elem['tasks'].extend(copy.deepcopy(ansible_tasks))
                    elif op == 'create':
                        if not v.is_software_component:
                            ansible_play_for_elem['tasks'].extend(copy.deepcopy(self.get_ansible_tasks_for_inputs(inputs)))
                            ansible_tasks = self.get_ansible_tasks_for_create(v, target_directory, node_filter_config,
                                                                              description_by_type, module_by_type,
                                                                              additional_args=extra)
                            ansible_tasks.extend(
                                self.get_ansible_tasks_from_interface(v, target_directory, is_delete, op,
                                                                      additional_args=extra))

                            ansible_play_for_elem['tasks'].extend(copy.deepcopy(ansible_tasks))
                            ansible_play_for_elem['tasks'].extend(copy.deepcopy(extra_tasks_for_delete))

                        else:
                            ansible_play_for_elem['hosts'] = v.host
                            ansible_play_for_elem['tasks'].extend(copy.deepcopy(
                                self.get_ansible_tasks_from_interface(v, target_directory, is_delete, op,
                                                                      additional_args=extra)))
                    else:
                        ansible_play_for_elem['tasks'].extend(copy.deepcopy(
                            self.get_ansible_tasks_from_interface(v, target_directory, is_delete, op,
                                                                  additional_args=extra)))
                ansible_playbook.append(ansible_play_for_elem)
                self.parallel_run([ansible_play_for_elem], v.name, q)
                active.append(v)
        if is_delete:
            last_play = dict(
                name='Renew id_vars_example.yaml',
                hosts=self.default_host,
                tasks=[]
            )
            last_play['tasks'].append(copy.deepcopy({FILE: {
                PATH: ids_file_path,
                STATE: 'absent'}}))
            self.parallel_run([last_play], None, q)
            done = q.get()
            if done != 'Done':
                logging.error("Something wrong with multiprocessing queue")
                sys.exit(1)
            ansible_playbook.append(last_play)
        return yaml.dump(ansible_playbook, default_flow_style=False, sort_keys=False)

    def init_graph(self, operations_graph):
        ts = TopologicalSorter(operations_graph)
        elements_queue = [*ts.static_order()]

        for v in elements_queue:
            self.gather_global_operations(v)
        for op_name, op in self.global_operations_info.items():
            self.global_operations_info[op_name] = self.replace_all_get_functions(op)
        for v in elements_queue:
            (_, element_type, _) = utils.tosca_type_parse(v.type)
            if element_type == NODES:
                new_conf_args = self.replace_all_get_functions(v.configuration_args)
                v.configuration_args = new_conf_args
            else:
                del operations_graph[v]
                for key in operations_graph:
                    if v in operations_graph[key]:
                        operations_graph[key].remove(v)
        return operations_graph

    def replace_all_get_functions(self, data):
        if isinstance(data, dict):
            if len(data) == 1 and data.get(GET_OPERATION_OUTPUT, None) is not None:
                full_op_name = '_'.join(data[GET_OPERATION_OUTPUT][:3]).lower()
                output_id = self.global_operations_info[full_op_name][OUTPUT_IDS][data[GET_OPERATION_OUTPUT][-1]]
                return self.rap_ansible_variable(output_id)
            if len(data) == 1 and data.get(GET_INPUT, None) is not None:
                output_id = self.global_variables['input_' + data[GET_INPUT]]
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

        configuration_args = {}
        for arg_key, arg in element_object.configuration_args.items():
            configuration_args[arg_key] = arg

        for interface_name, interface in self.get_interfaces_from_node(element_object).items():
            if interface_name == 'Prepare':
                for op_name, op in interface.items():
                    if op_name == 'configure':
                        op_key = '_'.join([element_object.name, interface_name.lower(), op_name])
                        if not self.global_operations_info.get(op_key, {}).get(OUTPUT_IDS):
                            tasks_from_op = self.get_ansible_tasks_from_operation(op_key, target_directory, True)
                            ansible_tasks.extend(tasks_from_op)
        ansible_args = copy.copy(element_object.configuration_args)
        ansible_args[STATE] = 'present'
        task_name = element_object.name.replace('-', '_')
        ansible_task_as_dict = dict()
        ansible_task_as_dict[NAME] = description_by_type
        ansible_task_as_dict[module_by_type] = configuration_args
        ansible_task_as_dict[REGISTER] = task_name
        ansible_task_as_dict.update(additional_args)
        ansible_tasks.append(ansible_task_as_dict)
        return ansible_tasks

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

    def get_ansible_tasks_from_interface(self, element_object, target_directory, is_delete, operation,
                                         additional_args=None):
        if additional_args is None:
            additional_args = {}
        else:
            additional_args_global = copy.deepcopy(additional_args.get('global', {}))
            additional_args_element = copy.deepcopy(additional_args.get(element_object.name, {}))
            additional_args = utils.deep_update_dict(additional_args_global,
                                                     additional_args_element)
        ansible_tasks = []
        scripts = []
        for interface_name, interface in self.get_interfaces_from_node(element_object).items():
            interface_operation = interface.get(operation, {})
            implementations = interface_operation.get(IMPLEMENTATION)
            if interface_name == 'Standard' and implementations is not None:
                if isinstance(implementations, six.string_types):
                    implementations = [implementations]
                scripts.extend(implementations)
                for script in implementations:
                    import_file = os.path.join(TMP_DIR, target_directory, os.path.basename(script))
                    os.makedirs(os.path.dirname(import_file), exist_ok=True)
                    copyfile(script, import_file)
                    if interface_operation.get(INPUTS) is not None:
                        for input_name, input_value in interface_operation[INPUTS].items():
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

    def copy_conditions_to_the_directory(self, conditions_set, target_directory):
        return

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
        if inputs is None:
            return
        for input_name, input in inputs.items():
            self.global_variables['input_' + input_name] = \
                input_name + '_' + str(utils.get_random_int(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))
        return

    def get_ansible_tasks_for_inputs(self, inputs):
        ansible_tasks = []
        for input_name, input in inputs.items():
            if input.get('default') is not None:
                ansible_tasks.append({
                    SET_FACT: {
                        input_name: input['default']
                    },
                    'when': input_name + IS_UNDEFINED
                })
            ansible_tasks.append({
                SET_FACT: {
                    self.global_variables['input_' + input_name]: self.rap_ansible_variable(input_name)
                }
            })
        return ansible_tasks

    def prepare_for_run(self):
        prepare_for_run()

    def parallel_run(self, ansible_play, name, q):
        parallel_run_ansible(ansible_play, name, q)
