import unittest
import copy
import os

from toscaparser.common.exception import MissingRequiredFieldError, ValidationError
from testing.base import BaseAnsibleProvider
from shell_clouni import shell
from toscatranslator.common.tosca_reserved_keys import TOSCA_DEFINITIONS_VERSION, TOPOLOGY_TEMPLATE, NODE_TEMPLATES, \
    TYPE, CAPABILITIES, PROPERTIES

from toscatranslator.common.utils import get_project_root_path


class TestKubernetesOutput(unittest.TestCase, BaseAnsibleProvider):
    PROVIDER = 'kubernetes'
    NODE_NAME = 'server-master'
    DEFAULT_TEMPLATE = {
        TOSCA_DEFINITIONS_VERSION: "tosca_simple_yaml_1_0",
        TOPOLOGY_TEMPLATE: {
            NODE_TEMPLATES: {
                NODE_NAME: {
                    TYPE: "tosca.nodes.Compute",
                    CAPABILITIES: {
                        'os': {
                            PROPERTIES: {
                                'type': 'ubuntu',
                                'distribution': 'xenial'
                            }
                        }
                    }
                }
            }
        }
    }

    def setUp(self):
        self.template = copy.deepcopy(self.DEFAULT_TEMPLATE)

    def tearDown(self):
        self.template = None
        self.delete_template(self.testing_template_filename())

    def test_validation(self):
        example_path = os.path.join(get_project_root_path(), 'examples', 'tosca-server-example-kubernetes.yaml')
        shell.main(['--template-file',  example_path, '--validate-only', '--cluster-name', 'test'])

    def test_k8s_translate(self):
        example_path = os.path.join(get_project_root_path(), 'examples', 'tosca-server-example-kubernetes.yaml')
        shell.main(
            ['--template-file', example_path, '--provider',
             self.PROVIDER, '--configuration-tool', 'kubernetes', '--cluster-name', 'test', '--debug'])

    def update_port(self, template):
        testing_parameter = {'endpoint': {'properties': {'port': 888}}}
        template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        for item in manifest:
            if item.get('kind') == 'Service':
                self.assertEqual(item.get('apiVersion'), 'v1')
                self.assertEqual(item.get('kind'), 'Service')
                self.assertEqual(item.get('metadata'), dict({'name': 'server-master-service'}))
        return manifest

    # testing a Service
    def test_private_address(self):
        template_1 = self.update_template_property(self.template, self.NODE_NAME, {'private_address': '10.233.0.2'})
        manifest = self.update_port(template_1)
        for m in manifest:
            if m.get('kind') == 'Service':
                self.assertEqual(m.get('spec'), {'clusterIP': '10.233.0.2', 'ports': [{'port': 888}]})

    @unittest.expectedFailure
    def test_private_address_error(self):
        with self.assertRaises(ValidationError):
            template = self.update_template_property(self.template, self.NODE_NAME,
                                                      {'private_address': '192.168.12.2578'})
            self.update_port(template)

    def test_private_address_with_protocol(self):
        template = self.update_template_property(self.template, self.NODE_NAME, {'private_address': '192.168.12.25'})
        testing_parameter = {'endpoint': {'properties': {'port': 888, 'protocol': 'TCP', 'port_name': 'test-ports'}}}
        template = self.update_template_capability(template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        for item in manifest:
            if item.get('kind') == 'Service':
                spec = item.get('spec', {})
                self.assertEqual(spec.get('clusterIP'), '192.168.12.25')
                self.assertEqual(len(spec.get('ports', [])), 1)
                self.assertEqual(spec['ports'][0].get('port'), 888)
                self.assertEqual(spec['ports'][0].get('protocol'), 'TCP')
                self.assertEqual(spec['ports'][0].get('targetPort'), 'test-ports')
            if item.get('kind') == 'Deployment':
                ports = item.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [{}])[0].get('ports', [])
                self.assertEqual(len(ports), 1)
                self.assertEqual(ports[0].get('name'), 'test-ports')
                self.assertEqual(ports[0].get('containerPort'), 888)

    def test_public_address(self):
        template = self.update_template_property(self.template, self.NODE_NAME, {'public_address': '192.168.12.25'})
        manifest = self.update_port(template)
        for m in manifest:
            if m.get('kind') == 'Service':
                self.assertEqual(m.get('spec'), {'externalIPs': ['192.168.12.25'], 'ports': [{'port': 888}]})

    def test_public_private_address(self):
        template = self.update_template_property(self.template, self.NODE_NAME, {'public_address': '192.168.12.25'})
        template = self.update_template_property(template, self.NODE_NAME, {'private_address': '10.233.0.2'})
        manifest = self.update_port(template)
        for m in manifest:
            if m.get('kind') == 'Service':
                self.assertEqual(m.get('spec'), {'externalIPs': ['192.168.12.25'],
                                                 'clusterIP': '10.233.0.2',
                                                 'ports': [{'port': 888}]})

    @unittest.expectedFailure
    def test_service_without_port(self):
        with self.assertRaises(MissingRequiredFieldError):
            template = self.update_template_property(self.template, self.NODE_NAME,
                                                      {'public_address': '192.168.12.25'})
            template = self.update_template_property(template, self.NODE_NAME, {'private_address': '192.168.12.24'})
            self.get_k8s_output(template)

    def test_service_with_targetPort(self):
        testing_parameter = {'endpoint': {'properties': {'port_name': "test-ports", 'port': 888}},
                             'os': {'properties': {'type': 'ubuntu', 'distribution': 'xenial'}}}
        template = self.update_template_capability(self.template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        for m in manifest:
            if m.get('kind') == 'Service':
                self.assertEqual(m.get('apiVersion'), 'v1')
                self.assertEqual(m.get('metadata'), dict({'name': 'server-master-service'}))
                self.assertEqual(m.get('spec'),
                                 {'ports': [{'port': 888, 'targetPort': 'test-ports'}],
                                  'selector': {'app': 'server-master'}})

    @unittest.expectedFailure
    def test_service_with_target_port_error(self):
        testing_parameter = {'endpoint': {'properties': {'port_name': "test-ports", 'port': 65555}},
                             'os': {'properties': {'type': 'ubuntu', 'distribution': 'xenial'}}}
        template = self.update_template_capability(self.template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)

    def test_host_capabilities(self):
        testing_parameter = {'os': {'properties': {'type': 'ubuntu', 'distribution': 'xenial'}}}
        template = self.update_template_capability(self.template, self.NODE_NAME, testing_parameter)
        manifest = self.get_k8s_output(template)
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0].get('apiVersion'), 'apps/v1')
        self.assertEqual(manifest[0].get('kind'), 'Deployment')
        self.assertEqual(manifest[0].get('metadata'),
                         {'name': 'server-master-deployment', 'labels': {'app': 'server-master'}})
        self.assertEqual(manifest[0].get('spec'), {'replicas': 1,
                                                   'selector': {'matchLabels': {'app': 'server-master'}},
                                                   'template': {'metadata': {'labels': {'app': 'server-master'}},
                                                                'spec': {'containers': [
                                                                    {'name': 'server-master-container',
                                                                     'image': 'ubuntu:xenial',
                                                                     'ports': [{'containerPort': 80}]}]}}})
