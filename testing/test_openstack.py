import unittest
from testing.base import TestAnsibleProviderOutput

SERVER_MODULE_NAME = 'os_server'


class TestAnsibleOpenStackOutput (unittest.TestCase, TestAnsibleProviderOutput):
    PROVIDER = 'openstack'

    def test_server_name(self):
        playbook = self.get_ansible_output()
        self.assertEqual(len(playbook), 1)
        self.assertIsInstance(playbook[0], dict)
        self.assertIsNotNone(playbook[0]['tasks'])
        tasks = playbook[0]['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertIsNotNone(tasks[0][SERVER_MODULE_NAME])
        server = tasks[0][SERVER_MODULE_NAME]
        self.assertEqual(server['name'], self.NODE_NAME)

    def test_meta(self):
        template = self.DEFAULT_TEMPLATE
        template['topology_template']['node_templates'][self.NODE_NAME].update({"meta": "master=true"})
        playbook = self.get_ansible_output(template)
        self.assertIsNotNone(next(next(playbook, {}).get('tasks', []), {}).get(SERVER_MODULE_NAME, {}).get('meta'))
        self.assertEqual(playbook[0]['tasks'][0][SERVER_MODULE_NAME]['meta'], "master=true")

