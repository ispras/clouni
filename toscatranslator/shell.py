import sys
import os
import argparse
from toscaparser.tosca_template import ToscaTemplate

from toscatranslator.common.translator_to_ansible import translate


class TranslatorShell(object):
    def get_parser(self, argv):
        parser = argparse.ArgumentParser(prog="tosca-tool")

        parser.add_argument('--template-file',
                            metavar='<filename>',
                            required=True,
                            help='YAML template to parse.')
        parser.add_argument('--validate-only',
                            action='store_true',
                            default=False,
                            help='Only validate input template, do not perform translation.')
        parser.add_argument('--provider',
                            required=False,
                            help='Cloud provider name to execute ansible playbook in.')
        parser.add_argument('--facts',
                            metavar='<filename>',
                            required=False,
                            help='Facts for cloud provider if provider parameter is used.')

        return parser

    def main(self, argv):

        parser = self.get_parser(argv)
        (args, args_list) = parser.parse_known_args(argv)
        template_path = args.template_file

        parsed_params={}
        a_file = os.path.isfile(template_path)
        if args.validate_only:
            ToscaTemplate(template_path, parsed_params, a_file)
            msg = ('The input "%(template_file)s" successfully passed '
                     'validation.') % {'template_file': template_path}
            print(msg)
            return
        if args.provider:
            output = translate(args.provider, template_path, args.facts, True)
            print (output)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    TranslatorShell().main(args)


if __name__ == '__main__':
    main()
