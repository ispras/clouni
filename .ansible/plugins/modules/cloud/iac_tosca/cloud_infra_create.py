#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: cloud_infra_create
short_description: Module to create infrastructure in cloud using TOSCA template
version_added: "0.1"
options:
  template:
    description: Path to the file, which contains TOSCA template
    required: true
author:
  - Shvetcova Valeriya (shvetcova@ispras.ru)
'''

EXAMPLES = '''
# Specify the template
- name: Create infrastructure using TOSCA template
    cloud_infra_create:
     template: openstack-server-example.yaml
    register: infra_result

- debug:
    var: infra_result
'''

RETURN = '''
role:
  description: role tasks to be executed
  returned: On success
  type: yaml
debug_output:
  description: output file for role.yaml if debug: true
  returned: On success
  sample: openstack-infra-playbook.yaml
'''

import os
from ansible.module_utils.basic import AnsibleModule

try:
    from translator.common.translator_to_ansible import translate as translator
    from translator.common.ansible_parameters import combine_facts_from_ansible_params, HAS_ARGUMENT_LIBS

    HAS_TOSCATOOL = True
except:
    HAS_TOSCATOOL = False

try:
    from ansible.module_utils.cloud_infra import cloud_infra_full_argument_spec

    HAS_CUSTOM_CLOUD_INFRA = True
except:
    HAS_CUSTOM_CLOUD_INFRA = False

# NOTE: Libraries' import is duplicated from translator.provider.common.combine_ansible_parameters


def main():
    # Check imported libs
    if not HAS_TOSCATOOL:
        raise ImportError(
            'Library tosca-tool is not found. Please install tosca-parser'
        )

    if not HAS_ARGUMENT_LIBS:
        raise ImportError(
            'Argument libraries could not be imported. Maybe you did not duplicated import '
            'from translator.provider.common.combine_ansible_parameters '
        )

    if not HAS_CUSTOM_CLOUD_INFRA:
        raise ImportError(
            'Ansible module_utils cloud_infra is not found. Please place it in your module_utils or '
            'in ~/.ansible/plugins/module_utils'
        )
    argument_spec = cloud_infra_full_argument_spec(
        template=dict(required=True, type='path'),
        cloud_provider=dict(type='str', required=True),
        debug=dict(default=False, type='bool'),
        debug_output=dict(type='path', required=False),
        facts=dict(required=False, type='dict'),
    )
    ansible_module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    # Get file content
    tosca_tpl = None
    file_exists = os.path.isfile(ansible_module.params['template'])
    if file_exists:
        with open(ansible_module.params['template']) as f:
            tosca_tpl = f.read()
    else:
        result = dict(
            rc=3,
            msg="Template not found in " + os.getcwd()
        )
        ansible_module.exit_json(**result)

    provider = ansible_module.params['cloud_provider']
    # import pydevd_pycharm
    # pydevd_pycharm.settrace('localhost', port=57777, stdoutToServer=True, stderrToServer=True)
    facts = combine_facts_from_ansible_params(provider, ansible_module.params)

    # # MAIN PART OF MODULE
    role = translator(provider, tosca_tpl, facts)
    #
    debug_output = ansible_module.params['debug_output']
    if not debug_output:
        debug_output = provider + '-infra-playbook.yaml'
    import json
    with open(debug_output, "w") as fo:
        fo.write(json.dumps(role))
    #
    result = dict(
        role=role,
        debug_output=debug_output
    )
    ansible_module.exit_json(**result)
    # ansible_module.exit_json()


if __name__ == '__main__':
    main()
