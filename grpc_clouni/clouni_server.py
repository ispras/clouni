from grpc_clouni.api_pb2 import ClouniResponse, ClouniRequest
import grpc_clouni.api_pb2_grpc as api_pb2_grpc
# import toscatranslator.shell as shell
from toscatranslator.common.translator_to_configuration_dsl import translate
from toscaparser.common.exception import ValidationError
from concurrent import futures
import logging
import grpc
import argparse
import sys
import atexit
import os
import six
import signal
from time import sleep
from functools import partial

def exit_gracefully(server, logger, x, y):
    server.stop(None)
    logger.info("Server stopped")
    sys.exit(0)

class TranslatorServer(object):
    def __init__(self, argv):
        self.template_file = argv['template_file_content']
        self.validate_only = argv['validate_only']
        self.is_delete = argv['delete']
        self.provider = argv['provider']
        self.output_file = None
        self.configuration_tool = argv['configuration_tool']
        self.cluster_name = argv['cluster_name']
        self.extra = argv['extra']

        if argv['async'] and not self.extra.get('async'):
            self.extra['async'] = args.async
        for k, v in self.extra.items():
            if isinstance(v, six.string_types):
                if v.isnumeric():
                    if int(v) == float(v):
                        self.extra[k] = int(v)
                    else:
                        self.extra[k] = float(v)

        self.working_dir = os.getcwd()

        self.output = translate(self.template_file, self.validate_only, self.provider, self.configuration_tool, self.cluster_name, self.is_delete,
                           extra={'global': self.extra}, a_file=False)

class ClouniServicer(api_pb2_grpc.ClouniServicer):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    def Clouni(self, request, context):
        self.logger.info("Request received")
        self.logger.debug("Request content: %s", str(request))
        args = self._RequestParse(request)
        response = ClouniResponse()
        try:
            if request.validate_only:
                self.logger.info("Validate only request - status TEMPLATE_VALID")
                response.status = ClouniResponse.Status.TEMPLATE_VALID
            else:
                self.logger.info("Request - status OK")
                response.status = ClouniResponse.Status.OK
            response.content = TranslatorServer(args).output

            self.logger.info("Response send")
            return response
        except ValidationError as err:
            self.logger.exception("\n")
            if request.validate_only:
                self.logger.info("Validate only request - status TEMPLATE_INVALID")
                response.status = ClouniResponse.Status.TEMPLATE_INVALID
            else:
                response.status = ClouniResponse.Status.ERROR
                self.logger.info("Request - status ERROR")
            response.error = str(err)
            self.logger.info("Response send")
            return response
        except Exception as err:
            self.logger.exception("\n")
            self.logger.info("Request - status ERROR")
            response.status = ClouniResponse.Status.ERROR
            response.error = str(err)
            self.logger.info("Response send")
            return response


    def _RequestParse(self, request):
        args = {}
        if request.template_file_content == "":
            raise Exception("Request field 'template_file_content' is required")
        else:
            args["template_file_content"] = request.template_file_content
        if request.cluster_name == "":
            raise Exception("Request field 'cluster_name' is required")
        else:
            args["cluster_name"] = request.cluster_name
        if request.validate_only:
            args['validate_only'] = True
        else:
            args['validate_only'] = False
        if request.delete:
            args['delete'] = True
        else:
            args['delete'] = False
        if request.provider != "":
            args['provider'] = request.provider
        else:
            args['provider'] = None
        if request.configuration_tool != "":
            args['configuration_tool'] = request.configuration_tool
        else:
            args['configuration_tool'] = 'ansible'
        if request.async:
            args['async'] = True
        else:
            args['async'] = False
        args['extra'] = {}
        for key, value in request.extra.items():
            args['extra'][key] = value
        return args


def parse_args(argv):
    parser = argparse.ArgumentParser(prog="clouni-server")

    parser.add_argument('--max-workers',
                        metavar='<number of workers>',
                        default=10,
                        type=int,
                        help='Maximum of working gRPC threads, default 10')

    parser.add_argument('--host',
                        metavar='<host_name/host_address>',
                        action='append',
                        help='Hosts on which server will be started, may be more than one, default [::]')
    parser.add_argument('--port', '-p',
                        metavar='<port>',
                        default=50051,
                        type=int,
                        help='Port on which server will be started, default 50051')
    parser.add_argument('--verbose', '-v',
                        action='count',
                        default=3,
                        help='Logger verbosity, default -vvv')
    parser.add_argument('--no-host-error',
                        action='store_true',
                        default=False,
                        help='If unable to start server on host:port and this option used, warning will be logged instead of critical error')
    parser.add_argument('--stop',
                        action='store_true',
                        default=False,
                        help='Stops all working servers and exit')
    try:
        args, args_list = parser.parse_known_args(argv)
    except argparse.ArgumentError:
        logging.critical("Failed to parse arguments. Exiting")
        sys.exit(1)
    return args.max_workers, args.host, args.port, args.verbose, args.no_host_error, args.stop

def serve(argv =  None):
    # Log init
    logger = logging.getLogger("Clouni server")
    # logger.setLevel(logging.INFO)
    fh = logging.FileHandler(".clouni-server.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    atexit.register(lambda logger: logger.info("Exited"), logger)
    # Argparse
    if argv is None:
        argv = sys.argv[1:]
    max_workers, hosts, port, verbose, no_host_error, stop = parse_args(argv)
    if stop:
        try:
            with open("/tmp/.clouni-server.pid", mode='r') as f:
                for line in f:
                    try:
                        os.kill(int(line), signal.SIGTERM)
                    except ProcessLookupError as e:
                        print(e)
            os.remove("/tmp/.clouni-server.pid")
        except FileNotFoundError:
            print("Working servers not found: no .clouni-server.pid file in this directory")
        sys.exit(0)
    # Verbosity choose
    if verbose == 1:
        logger.info("Logger level set to ERROR")
        logger.setLevel(logging.ERROR)
    elif verbose == 2:
        logger.info("Logger level set to WARNING")
        logger.setLevel(logging.WARNING)
    elif verbose == 3:
        logger.info("Logger level set to INFO")
        logger.setLevel(logging.INFO)
    else:
        logger.info("Logger level set to DEBUG")
        logger.setLevel(logging.DEBUG)

    if hosts is None:
        hosts = ['[::]', ]
    logger.info("Logging clouni-server started")
    logger.debug("Arguments succesfully parsed: max_workers %s, port %s, host %s", max_workers, port, str(hosts))
    # Argument check
    if max_workers < 1:
        logger.critical("Invalid max_workers argument: should be greater than 0. Exiting")
        sys.exit(1)
    if port == 0:
        logger.warning("Port 0 gived - port will be runtime choosed - may be an error")
    if port < 0:
        logger.critical("Invalid port argument: should be greater or equal than 0. Exiting")
        sys.exit(1)
    # Starting server
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        api_pb2_grpc.add_ClouniServicer_to_server(
            ClouniServicer(logger), server)

        host_exist = False
        for host in hosts:
            try:
                port = server.add_insecure_port(host+":"+str(port))
                host_exist = True
                logger.info("Server is going to start on %s:%s", host, port)
            except:
                if no_host_error:
                    logger.warning("Failed to start server on %s:%s", host, port)
                else:
                    logger.error("Failed to start server on %s:%s", host, port)
                    sys.exit(1)
        if host_exist:
            with open("/tmp/.clouni-server.pid", mode='a') as f:
                f.write(str(os.getpid()) + '\n')
            server.start()
            logger.info("Server started")
        else:
            logger.critical("No host exists")
            sys.exit(1)
    except Exception:
        logger.critical("Unable to start the server")
        sys.exit(1)
    signal.signal(signal.SIGINT, partial(exit_gracefully, server, logger))
    signal.signal(signal.SIGTERM, partial(exit_gracefully, server, logger))
    while True:
        sleep(100)

if __name__ == '__main__':
    serve()
