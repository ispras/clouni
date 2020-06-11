import unittest
from testing.base import TestAnsibleProvider
import os

from toscatranslator import shell

SERVER_MODULE_NAME = 'os_server'
PORT_MODULE_NAME = 'os_port'
FIP_MODULE_NAME = 'os_floating_ip'
SEC_GROUP_MODULE_NAME = 'os_security_group'
SEC_RULE_MODULE_NAME = 'os_security_group_rule'


class TestAnsibleMichmanTemplatesOutput (unittest.TestCase, TestAnsibleProvider):
    PROVIDER = 'openstack'

    def get_tpl_path(self, file_name):
        return os.path.join('launcher-templates', file_name)

    def test_master_with_ip_pool(self):
        file_path = self.get_tpl_path('master-with-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3'])

    def test_master_without_ip_pool(self):
        file_path = self.get_tpl_path('master-without-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3'])

    def test_master_with_ip_pool_async(self):
        file_path = self.get_tpl_path('master-with-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])

    def test_master_without_ip_pool_async(self):
        file_path = self.get_tpl_path('master-without-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])

    def test_slaves_with_ip_pool(self):
        file_path = self.get_tpl_path('slaves-with-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3'])

    def test_slaves_without_ip_pool(self):
        file_path = self.get_tpl_path('slaves-without-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3'])

    def test_slaves_with_ip_pool_async(self):
        file_path = self.get_tpl_path('slaves-with-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])

    def test_slaves_without_ip_pool_async(self):
        file_path = self.get_tpl_path('slaves-without-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])

    def test_storage_with_ip_pool(self):
        file_path = self.get_tpl_path('storage-with-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3'])

    def test_storage_without_ip_pool(self):
        file_path = self.get_tpl_path('storage-without-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3'])

    def test_storage_with_ip_pool_async(self):
        file_path = self.get_tpl_path('storage-with-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])

    def test_storage_without_ip_pool_async(self):
        file_path = self.get_tpl_path('storage-without-ip-pool.yaml')
        shell.main(['--template-file', file_path, '--provider', self.PROVIDER, '--extra', 'retries=3', 'async=60', 'poll=0', 'delay=1'])
