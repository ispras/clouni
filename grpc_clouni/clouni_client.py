from grpc_clouni.api_pb2 import ClouniResponse, ClouniRequest
import grpc_clouni.api_pb2_grpc as api_pb2_grpc
import grpc
import sys
import os
import argparse

def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser(prog="clouni-client")

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
    parser.add_argument('--delete',
                        action='store_true',
                        default=False,
                        help='Delete cluster')
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
    parser.add_argument('--host',
                        metavar='<host_name/host_address>',
                        default='localhost',
                        help='Host of server, default localhost')
    parser.add_argument('--port', '-p',
                        metavar='<port>',
                        default=50051,
                        type=int,
                        help='Port of server, default 50051')

    (args, args_list) = parser.parse_known_args(args)
    channel = grpc.insecure_channel(args.host+':'+str(args.port))
    stub = api_pb2_grpc.ClouniStub(channel)

    request = ClouniRequest()

    template_file = os.path.join(os.getcwd(), args.template_file)
    with open(template_file, 'r') as f:
        template_content = f.read()
    request.template_file_content = template_content
    request.cluster_name = args.cluster_name
    request.validate_only = args.validate_only
    request.delete = args.delete
    if args.provider is not None:
        request.provider = args.provider
    else:
        request.provider = ""
    request.configuration_tool = args.configuration_tool
    request.async = args.async

    extra = {}
    for i in args.extra:
        i_splitted = [j.strip() for j in i.split('=', 1)]
        if len(i_splitted) < 2:
            raise Exception('Failed parsing parameter \'--extra\', required \'key=value\' format')
        extra.update({i_splitted[0]: i_splitted[1]})
    if args.async and not extra.get('async'):
        extra['async'] = args.async

    for k, v in extra.items():
        if isinstance(v, six.string_types):
            if v.isnumeric():
                if int(v) == float(v):
                    extra[k] = int(v)
                else:
                    extra[k] = float(v)
        request.extra = [k, v]

    response = stub.Clouni(request)
    print("* Status *\n")
    status = ['TEMPLATE_VALID', 'TEMPLATE_INVALID', 'OK', 'ERROR']
    print(status[response.status])
    print("\n* Error *\n")
    print(response.error)
    print("\n* Content *\n")
    print(response.content)
