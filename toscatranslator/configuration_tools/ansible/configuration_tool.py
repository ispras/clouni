from toscatranslator.configuration_tools.common.configuration_tool import *
from toscatranslator.common.tosca_reserved_keys import PARAMETERS, VALUE, EXTRA, SOURCE, GET_OPERATION_OUTPUT, INPUTS


import copy, yaml, os, itertools

REGISTER = 'register'
DEFAULT_HOST = 'localhost'
SET_FACT_MODULE = 'set_fact'
IMPORT_TASKS_MODULE = 'import_tasks'


class AnsibleConfigurationTool(ConfigurationTool):
    """
    Must be tested by TestAnsibleOpenstack.test_translating_to_ansible
    """

    def to_dsl_for_create(self, provider, nodes_relationships_queue):
        for v in nodes_relationships_queue:
            self.gather_global_operations(v)

        for op_name, op in self.global_operations_info.items():
            self.global_operations_info[op_name] = self.replace_all_get_functions(op)

        elements_queue = []
        for v in nodes_relationships_queue:
            (_, element_type, _) = tosca_type.parse(v.type)
            if element_type == NODES:
                new_conf_args =  self.replace_all_get_functions(v.configuration_args)
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

        ansible_args = copy.copy(element_object.configuration_args)
        ansible_args['state'] = 'present'
        self.ansible_task_as_dict = dict()
        self.ansible_task_as_dict['name'] = self.ansible_description_by_type(element_object)
        self.ansible_task_as_dict[self.ansible_module_by_type(element_object)] = \
            element_object.configuration_args
        self.ansible_task = yaml.dump(self.ansible_task_as_dict)

        return [self.ansible_task_as_dict]

    def ansible_description_by_type(self, provider_source_obj):
        return "Create element"

    def ansible_module_by_type(self, provider_source_obj):
        return "os_" + provider_source_obj.type_name.lower()

    def get_ansible_tasks_from_operation(self, op_name):
        tasks = []

        op_info = self.global_operations_info[op_name]
        if not op_info.get(OUTPUT_IDS) or not op_info.get(IMPLEMENTATION):
            return []

        import_task_arg = op_info[IMPLEMENTATION]
        if op_info.get(INPUTS):
            for k, v in op_info[INPUTS].items():
                arg_v = v

                if isinstance(v, (dict, list, set, tuple)):
                    seed(time)
                    arg_v = '_'.join([k, str(randint(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))])
                    arg_v = self.rap_ansible_variable(arg_v)
                    new_task = {
                        SET_FACT_MODULE: {
                            arg_v: v
                        }
                    }
                    tasks.append(new_task)
                arg_k = k
                temp_arg = arg_k + '=' + arg_v
                import_task_arg += ' ' + temp_arg

        new_task = {
            IMPORT_TASKS_MODULE: import_task_arg
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

    def create_artifact(self, filename, data):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
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

        with open(filename, "w") as f:
            filedata = yaml.dump(tasks)
            f.write(filedata)

        return
