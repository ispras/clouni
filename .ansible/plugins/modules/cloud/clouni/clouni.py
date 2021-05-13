#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

# TODO add module information

DOCUMENTATION = '''
---
module: clouni
short_description: Module to create infrastructure in cloud using TOSCA template
version_added: "0.1"
options:
  template_file:
    description: Path to the file, which contains TOSCA template
    required: true
author:
  - Shvetcova Valeriya (shvetcova@ispras.ru)
'''

EXAMPLES = '''
# Specify the template
- name: Create infrastructure using TOSCA template
    clouni:
     template_file: tosca-server-example.yaml
     provider: openstack
     cluster_name: testing_ansible
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

from ansible.module_utils.basic import AnsibleModule


def main():
    # Import toscatranslator modules
    import importlib
    translator_to_configuration_dsl_lib = importlib.import_module('toscatranslator.common.translator_to_configuration_dsl')
    translator = translator_to_configuration_dsl_lib.translate
    parser_exception_lib = importlib.import_module('toscaparser.common.exception')

    argument_spec = dict(
        template_file=dict(type='path', required=True),
        validate_only=dict(type='bool', default=False),
        provider=dict(type='str', required=True, choices=['openstack', 'amazon', 'kubernetes']),
        configuration_tool=dict(type='str', default='ansible', choices=['ansible', 'kubernetes']),
        cluster_name=dict(type='str', required=True),
        state=dict(type='str', default='present', choices=['present', 'absent']),
        extra=dict(type='str', default=None),
        output_playbook_name=dict(type='path', required=False),
    )
    ansible_module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    template_file = ansible_module.params['template_file']
    validate_only = ansible_module.params['validate_only']
    provider = ansible_module.params['provider']
    configuration_tool = ansible_module.params['configuration_tool']
    cluster_name = ansible_module.params['cluster_name']
    state = ansible_module.params['state']
    is_delete = False
    if state == 'absent':
        is_delete = True
    a_file = True
    extra = ansible_module.params['extra']
    try:
        stdout = translator(template_file, validate_only, provider, configuration_tool, cluster_name, is_delete,
                            a_file, extra)
        result = dict()
        output_file = ansible_module.params['output_playbook_name']
        if output_file:
            with open(output_file, 'w') as file_obj:
                file_obj.write(stdout)
            result['msg_file'] = output_file
        else:
            result['msg'] = stdout

        ansible_module.exit_json(**result)

    except parser_exception_lib.TOSCAException as err:
        ansible_module.fail_json(msg=err.message)


if __name__ == '__main__':
    main()
