# tosca-tool
Cloud Application Management Tool by TOSCA

## Installation
`tosca-tool` requires Python 3.7 to be used.

To install `tosca-tool` is recommended to create virtual environment and install requirements in your environment. 

Installation command
~~~shell
cd $TOSCA_TOOL_HOME
python setup.py install
~~~

## Usage

Execute
~~~shell 
tosca-tool --help
~~~
Output
~~~
usage: tosca-tool [-h] --template-file <filename> [--validate-only]
                  [--provider PROVIDER] [--facts <filename>]

optional arguments:
  -h, --help            show this help message and exit
  --template-file <filename>
                        YAML template to parse.
  --validate-only       Only validate input template, do not perform
                        translation.
  --provider PROVIDER   Cloud provider name to execute ansible playbook in.
  --facts <filename>    Facts for cloud provider if provider parameter is
                        used.
~~~

Example
~~~shell
tosca-tool --template-file tosca-server-example.yaml
~~~

