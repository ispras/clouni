import sys
import argparse
import os
import six

from toscatranslator.common.translator_to_configuration_dsl import translate


class TranslatorShell(object):
    def __init__(self, argv):

        parser = self.get_parser()
        (args, args_list) = parser.parse_known_args(argv)

        self.template_file = args.template_file
        self.validate_only = args.validate_only
        self.provider = args.provider
        self.output_file = args.output_file
        self.configuration_tool = args.configuration_tool
        self.cluster_name = args.cluster_name
        self.extra = {}
        for i in args.extra:
            i_splitted = [j.strip() for j in i.split('=', 1)]
            if len(i_splitted) < 2:
                raise Exception('Failed parsing parameter \'--extra\', required \'key=value\' format')
            self.extra.update({i_splitted[0]: i_splitted[1]})
        if args.async and not self.extra.get('async'):
            self.extra['async'] = args.async

        for k, v in self.extra.items():
            if isinstance(v, six.string_types):
                if v.isnumeric():
                    if int(v) == float(v):
                        self.extra[k] = int(v)
                    else:
                        self.extra[k] = float(v)

        self.working_dir = os.getcwd()

        output = translate(self.template_file, self.validate_only, self.provider, self.configuration_tool, self.cluster_name,
                           extra={'global': self.extra})
        self.output_print(output)

    def get_parser(self):
        parser = argparse.ArgumentParser(prog="clouni")

        parser.add_argument('--template-file',
                            metavar='<filename>',
                            required=True,
                            help='YAML template to parse.')
        parser.add_argument('--cluster-name',
                            required=True,
                            help='Cluster name')
        parser.add_argument('--validate-only',
                            action='store_true',
                            default=False,
                            help='Only validate input template, do not perform translation.')
        parser.add_argument('--provider',
                            required=False,
                            help='Cloud provider name to execute ansible playbook in.')
        parser.add_argument('--output-file',
                            metavar='<filename>',
                            required=False,
                            help='Output file')
        parser.add_argument('--configuration-tool',
                            default="ansible",
                            help="Configuration tool which DSL the template would be translated to. "
                                 "Default value = \"ansible\"")
        parser.add_argument('--async',
                            action='store_true',
                            default=False,
                            help='Provider nodes should be created asynchronously')
        parser.add_argument('--extra',
                            default=[],
                            metavar="KEY=VALUE",
                            nargs='+',
                            help='Extra arguments for configuration tool scripts')

        return parser

    def output_print(self, output_msg):
        if self.output_file:
            with open(self.output_file, 'w') as file_obj:
                file_obj.write(output_msg)
        else:
            print(output_msg)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    TranslatorShell(args)


if __name__ == '__main__':
    main()
