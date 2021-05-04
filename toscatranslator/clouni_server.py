from toscatranslator.api_pb2 import ClouniResponse, ClouniRequest
import toscatranslator.api_pb2_grpc as api_pb2_grpc
import toscatranslator.shell as shell
from toscaparser.common.exception import ValidationError
from concurrent import futures
import logging
import grpc
import argparse
import sys
import atexit

class ClouniServicer(api_pb2_grpc.ClouniServicer):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    def Clouni(self, request, context):
        self.logger.info("Request received")
        args = self._RequestParse(request)
        print(args)
        response = ClouniResponse()
        try:
            if request.validate_only:
                self.logger.info("Validate only request - status TEMPLATE_VALID")
                response.status = ClouniResponse.Status.TEMPLATE_VALID
            else:
                self.logger.info("Request - status OK")
                response.status = ClouniResponse.Status.OK
            response.content = shell.TranslatorShell(args, server=True)

            self.logger.info("Response send")
            return response
        except ValidationError as err:
            self.logger.exception("")
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
            self.logger.exception("")
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

    parser.add_argument('--max_workers',
                        metavar='<number of workers>',
                        default=10,
                        type=int,
                        help='Maximum of working gRPC threads, default 10')

    parser.add_argument('--port', '-p',
                        metavar='<port>',
                        default=50051,
                        type=int,
                        help='Port on which server will be started, default 50051')
    parser.add_argument('--verbose', '-v',
                        action='count',
                        default=3,
                        help='Logger verbosity, default -vvv')
    try:
        args, args_list = parser.parse_known_args(argv)
    except argparse.ArgumentError:
        logging.critical("Failed to parse arguments. Exiting")
        sys.exit(1)
    return args.max_workers, args.port, args.verbose

def serve(argv =  None):
    # Log init
    logger = logging.getLogger("Clouni server")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(".clouni-server.log")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(threadName)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("Logging clouni-server started")
    atexit.register(lambda logger: logger.info("Exited"), logger)
    # Argparse
    if argv is None:
        argv = sys.argv[1:]
    max_workers, port, verbose = parse_args(argv)
    logger.info("Arguments succesfully parsed: max_workers %s, port %s", max_workers, port)

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

    request = ClouniRequest(extra={'key1':'value1', 'key2':'value2'}, provider='qwerty', template_file_content="qwe", cluster_name='asd')
    print(ClouniServicer(logger).Clouni(request, 1))
    try:
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        api_pb2_grpc.add_ClouniServicer_to_server(
            ClouniServicer(logger), server)
        port = server.add_insecure_port('[::]:'+str(port))
        server.start()
        logger.info("Server started on port %s", port)
    except Exception:
        logger.critical("Unable to start the server. Exiting")
        sys.exit(1)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(None)
        logger.info("Server stopped")


if __name__ == '__main__':
    serve()
