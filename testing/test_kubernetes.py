import unittest
import copy
import os

from toscaparser.common.exception import MissingRequiredFieldError, ValidationError
from testing.base import BaseAnsibleProvider
from toscatranslator import shell
from toscatranslator.common.tosca_reserved_keys import TOSCA_DEFINITIONS_VERSION, TOPOLOGY_TEMPLATE, NODE_TEMPLATES, TYPE

from toscatranslator.common.utils import get_project_root_path


class TestKubernetesOutput(unittest.TestCase, BaseAnsibleProvider):
    PROVIDER = 'kubernetes'
    NODE_NAME = 'server-master'
    DEFAULT_TEMPLATE = {
        TOSCA_DEFINITIONS_VERSION: "tosca_simple_yaml_1_0",
        TOPOLOGY_TEMPLATE: {
            NODE_TEMPLATES: {
                NODE_NAME: {
                    TYPE: "tosca.nodes.Compute"
                }
            }
        }
    }

    def setUp(self):
        self.template = copy.deepcopy(self.DEFAULT_TEMPLATE)

    def tearDown(self):
        self.template = None
        self.delete_template(self.testing_template_filename())

    # FIXME:  bug 7606
    # @unittest.skip
    def test_validation(self):
        example_path = os.path.join(get_project_root_path(), 'examples', 'tosca-server-example-kubernetes.yaml')
        shell.main(['--template-file',  example_path, '--validate-only', '--cluster-name', 'test'])

    def test_k8s_translate(self):
        example_path = os.path.join(get_project_root_path(), 'examples', 'tosca-server-example-kubernetes.yaml')
        shell.main(
            ['--template-file', example_path, '--provider',
             self.PROVIDER, '--configuration-tool', 'kubernetes', '--cluster-name', 'test'])

    def update_port(self, template):
        testing_parameter = {'endpoint': {'properties': {'port': 888}}}
        template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        self.assertEqual(manifest[0].get('apiVersion'), 'v1')
        self.assertEqual(manifest[0].get('kind'), 'Service')
        self.assertEqual(manifest[0].get('metadata'), dict({'name': 'server-master-service'}))
        return manifest

    # testing a Service
    def test_private_address(self):
        template_1 = self.update_template_attribute(self.template, self.NODE_NAME, {'private_address': '10.233.0.2'})
        manifest = self.update_port(template_1)
        self.assertEqual(manifest[0].get('spec'), {'clusterIP': '10.233.0.2', 'ports': [{'port': 888}]})


    def test_private_address_error(self):
        with self.assertRaises(ValidationError):
            template = self.update_template_attribute(self.template, self.NODE_NAME,
                                                      {'private_address': '192.168.12.2578'})
            self.update_port(template)

    # FIXME:  bug 7606
    @unittest.expectedFailure
    def test_private_address_with_protocol(self):
        template = self.update_template_attribute(self.template, self.NODE_NAME, {'private_address': '192.168.12.25'})
        testing_parameter = {'endpoint': {'properties': {'port': 888, 'protocol': 'TCP'}}}
        template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        self.assertEqual(manifest[0].get('spec'),
                         {'clusterIP': '192.168.12.25', 'ports': [{'port': 888, 'protocol': 'TCP'}]})

    def test_public_address(self):
        template = self.update_template_attribute(self.template, self.NODE_NAME, {'public_address': '192.168.12.25'})
        manifest = self.update_port(template)
        self.assertEqual(manifest[0].get('spec'), {'externalIPs': ['192.168.12.25'], 'ports': [{'port': 888}]})

    def test_public_private_address(self):
        template = self.update_template_attribute(self.template, self.NODE_NAME, {'public_address': '192.168.12.25'})
        template = self.update_template_attribute(template, self.NODE_NAME, {'private_address': '10.233.0.2'})
        manifest = self.update_port(template)
        self.assertEqual(manifest[0].get('spec'),
                         {'externalIPs': ['192.168.12.25'], 'clusterIP': '10.233.0.2', 'ports': [{'port': 888}]})

    def test_service_without_port(self):
        with self.assertRaises(MissingRequiredFieldError):
            template = self.update_template_attribute(self.template, self.NODE_NAME,
                                                      {'public_address': '192.168.12.25'})
            template = self.update_template_attribute(template, self.NODE_NAME, {'private_address': '192.168.12.24'})
            self.get_k8s_output(template)
    # FIXME:  bug 7606
    @unittest.expectedFailure
    def test_service_with_targetPort(self):
        testing_parameter = {'endpoint': {'properties': {'port_name': 8000, 'port': 888}},
                             'os': {'properties': {'type': 'ubuntu', 'distribution': 'xenial'}}}
        template = self.update_template_capability(self.template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        self.assertEqual(manifest[1].get('apiVersion'), 'v1')
        self.assertEqual(manifest[1].get('kind'), 'Service')
        self.assertEqual(manifest[1].get('metadata'), dict({'name': 'server_master-service'}))
        self.assertEqual(manifest[1].get('spec'),
                         {'ports': [{'targetPort': 8000}], 'selector': {'app': 'server_master'}})
        testing_parameter = {'endpoint': {'properties': {'port_name': 65555}}}
        template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)


    # testing a Deployment
    # FIXME:  bug 7606
    @unittest.expectedFailure
    def test_host_capabilities(self):
        testing_parameter = {'os': {'properties': {'type': 'ubuntu', 'distribution': 'xenial'}}}
        template = self.update_template_capability(self.template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        self.assertEqual(manifest[0].get('apiVersion'), 'apps/v1')
        self.assertEqual(manifest[0].get('kind'), 'Deployment')
        self.assertEqual(manifest[0].get('metadata'),
                         {'name': 'server_master-deployment', 'labels': {'app': 'server_master'}})
        self.assertEqual(manifest[0].get('spec'), {'replicas': 1,
                                                   'template': {'metadata': {'labels': {'app': 'server_master'}},
                                                                'spec': {'containers': [
                                                                    {'name': 'server_master-container'}]}}})
