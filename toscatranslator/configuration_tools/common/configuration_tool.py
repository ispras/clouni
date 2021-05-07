import six
import copy

from toscatranslator.common import utils
from toscatranslator.common.tosca_reserved_keys import NODES, RELATIONSHIPS, INTERFACES, GET_OPERATION_OUTPUT, SELF, \
    IMPLEMENTATION

from toscaparser.common.exception import ExceptionCollector
from toscatranslator.common.exception import TemplateDependencyError

from toscatranslator.configuration_tools.common.tool_config import ConfigurationToolConfiguration


OUTPUT_IDS = 'output_ids'
OUTPUT_ID_RANGE_START = 1000
OUTPUT_ID_RANGE_END = 9999


class ConfigurationTool(object):

    def __init__(self):
        if not hasattr(self, 'TOOL_NAME'):
            raise NotImplementedError()

        self.global_operations_queue = []
        self.global_operations_info = {}
        self.global_variables = {}

        self.tool_config = ConfigurationToolConfiguration(self.TOOL_NAME)

    def to_dsl(self, provider, nodes_relationships_queue, cluster_name, is_delete, artifacts=None,
               target_directory=None, extra=None):
        """
        Generate scenarios for configuration tool to execute
        :param provider: provider type key name
        :param nodes_relationships_queue: can be of class ProviderResource or RelationshipTemplate
        :param cluster_name: unified name of cluster of template
        :param is_delete: boolean value that means if scenario should create or delete cluster
        :param artifacts: list of artifacts that are mentioned in template
        :param target_directory: directory where copy artifacts
        :param extra: extra parameters for configuration tool scenarios
        :return: string with dsl scenario which is used to deploy
        """
        raise NotImplementedError()

    def create_artifact(self, filename, data):
        """

        :param filename:
        :param data:
        :return:
        """
        raise NotImplementedError()

    def gather_global_operations(self, element_object):
        """

        :param element_object:
        :return:
        """

        interfaces = []
        element_template_name = None
        (_, element_type, _) = utils.tosca_type_parse(element_object.type)
        if element_type == NODES:
            interfaces = self.get_interfaces_from_node(element_object)
            element_template_name = element_object.name
            op_required = self.list_get_operation_outputs(element_object.nodetemplate.entity_tpl)
            self.manage_operation_output(op_required, element_template_name)
        elif element_type == RELATIONSHIPS:
            # NOTE interfaces can't be used as it contains the error ()
            interfaces = self.get_interfaces_from_relationship(element_object)
            element_template_name = element_object.name

        if not element_template_name:
            return

        operations = {}
        for interface_name, ops in interfaces.items():
            for operation_name, operation_data in ops.items():
                operations['_'.join([interface_name.lower(), operation_name])] = operation_data

        # Sort operations by dependency
        prev_len = len(operations) + 1
        required_operations = {}
        for op_name, op in operations.items():
            if isinstance(op, six.string_types):
                op = {
                    IMPLEMENTATION: op
                }
            op_required = self.list_get_operation_outputs(op)
            required_operations[op_name] = op_required
            self.manage_operation_output(op_required, element_template_name)

        while len(operations) > 0 and prev_len > len(operations):
            ops_for_iter = copy.deepcopy(operations)
            prev_len = len(operations)
            for op_name, op in ops_for_iter.items():
                op_required = required_operations[op_name]
                if_executable_now = True
                for i in op_required:
                    if i[0] == SELF:
                        i[0] = element_template_name
                    temp_op_name = '_'.join(i[:3]).lower()
                    if temp_op_name not in self.global_operations_queue:
                        if_executable_now = False
                        break
                if if_executable_now:
                    temp_op_name = '_'.join([element_template_name, op_name]).lower()
                    self.global_operations_queue.append(temp_op_name)
                    updating_op_info = {
                        temp_op_name: op
                    }
                    utils.deep_update_dict(self.global_operations_info, updating_op_info)
                    operations.pop(op_name)

        if len(operations) > 0:
            ExceptionCollector.appendException(TemplateDependencyError(
                what=element_template_name
            ))

    def get_interfaces_from_node(self, node):
        # TODO
        """

        :param node:
        :return:
        """
        return node.nodetemplate.entity_tpl.get(INTERFACES, {})

    def get_interfaces_from_relationship(self, rel):
        """

        :param rel:
        :return:
        """
        return rel.entity_tpl.get(INTERFACES, {})

    def manage_operation_output(self, op_required, element_template_name):
        """

        :param op_required:
        :param element_template_name:
        :return:
        """
        for o in op_required:
            if o[0] == SELF:
                o[0] = element_template_name
            temp_op_name = '_'.join(o[:3]).lower()

            output_id = o[-1] + '_' + str(utils.get_random_int(OUTPUT_ID_RANGE_START, OUTPUT_ID_RANGE_END))
            updating_op_info = {
                temp_op_name: {
                    OUTPUT_IDS: {
                        o[-1]: output_id
                    }
                }
            }
            utils.deep_update_dict(self.global_operations_info, updating_op_info)

    def list_get_operation_outputs(self, data):
        """

        :param data:
        :return:
        """
        required_operations = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k == GET_OPERATION_OUTPUT:
                    required_operations.append(v)
                else:
                    required_operations.extend(self.list_get_operation_outputs(v))
        elif isinstance(data, list):
            for v in data:
                required_operations.extend(self.list_get_operation_outputs(v))

        return required_operations

    def copy_conditions_to_the_directory(self, used_conditions_set, directory):
        raise NotImplementedError()

    def get_artifact_extension(self):
        raise NotImplementedError()
