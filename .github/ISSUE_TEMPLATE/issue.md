---
name: Issue
about: Create a bug report or feature request to help us improve
title: ''
labels: ''
assignees: bura2017

---

**Clouni CLI command which was executed**
clouni --template-file test_template.yaml --cluster-name test

**Input TOSCA template**
~~~yaml
tosca_definitions_version: tosca_simple_yaml_1_0

topology_template:
  node_templates:
    tosca_server_example:
      type: tosca.nodes.Compute
~~~

**Current result**
~~~yaml
- hosts: localhost
  tasks: <...>
~~~

**Expected result**
Example resulting script or description of resulting cloud resources

**Describe the bug**
A clear and concise description of what the bug or feature is.

**Additional context**
Add any other context about the problem here.
