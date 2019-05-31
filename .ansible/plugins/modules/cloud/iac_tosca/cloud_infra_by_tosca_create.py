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
module: cloud_infra_by_tosca_create
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
    cloud_infra_by_tosca_create:
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

from ansible.module_utils.basic import AnsibleModule

import ansible.module_utils.cloud_infra_by_tosca as cibt


def main():
    # Import toscatranslator modules
    import importlib
    translator_to_ansible_lib = importlib.import_module('toscatranslator.common.translator_to_ansible')
    translator = translator_to_ansible_lib.translate
    parser_exception_lib = importlib.import_module('toscaparser.common.exception')
    translator_exception_lib = importlib.import_module('toscatranslator.common.exception')

    argument_spec = cibt.cloud_infra_full_argument_spec(
        template_file=dict(type='path', required=True),
        validate_only=dict(type='bool', required=False),
        translate_only=dict(type='bool', required=False),
        provider=dict(type='str', required=False),
        facts=dict(type='dict', required=False),
        output_file=dict(type='path', required=False),
    )
    ansible_module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    template_file = ansible_module.params['template_file']
    validate_only = ansible_module.params['validate_only']
    translate_only = ansible_module.params['translate_only']
    provider = ansible_module.params['provider']
    facts = cibt.combine_facts_from_ansible_params(provider, ansible_module.params)
    if facts is None:
        raise translator_exception_lib.UnspecifiedFactsParserForProviderError(what=provider)
    try:
        stdout = translator(template_file, validate_only, provider, facts)
        result = dict()
        output_file = ansible_module.params['output_file']
        if output_file:
            with open(output_file, 'w') as file_obj:
                file_obj.write(stdout)
            result['msg_file'] = output_file
        else:
            result['msg'] = stdout

        if validate_only or translate_only:
            ansible_module.exit_json(**result)

        raise NotImplementedError()

    except parser_exception_lib.TOSCAException as err:
        ansible_module.fail_json(msg=err.message)


if __name__ == '__main__':
    main()
