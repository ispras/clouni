from toscatranslator.api_pb2 import ClouniResponse, ClouniRequest
import toscatranslator.api_pb2_grpc as api_pb2_grpc
import toscatranslator.shell as shell
from toscaparser.common.exception import ValidationError
from concurrent import futures
import logging
import grpc
import sys

class ClouniServicer(api_pb2_grpc.ClouniServicer):

    def Clouni(self, request, context):
        args = self._RequestParse(request)
        response = ClouniResponse()
        try:
            if request.validate_only:
                response.status = ClouniResponse.Status.TEMPLATE_VALID
            else:
                response.status = ClouniResponse.Status.OK
            response.content = shell.TranslatorShell(args, server_return=True)
            return response
        except ValidationError as err:
            if request.validate_only:
                response.status = ClouniResponse.Status.TEMPLATE_INVALID
            else:
                response.status = ClouniResponse.Status.ERROR
            response.error = str(err)
            return response
        except Exception as err:
            response.status = ClouniResponse.Status.ERROR
            response.error = str(err)
            return response

            
    def _RequestParse(self, request):
        args = []
        if request.template_file_content == "":
            raise Exception("Request field 'template_file_content' is required")
        else:
            args.append("--template-file")
            args.append(request.template_file_content)
        if request.cluster_name == "":
            raise Exception("Request field 'cluster_name' is required")
        else:
            args.append("--cluster-name")
            args.append(request.cluster_name)
        if request.validate_only:
            args.append("--validate-only")
        if request.delete:
            args.append("--delete")
        if request.provider == "":
            args.append("--provider")
            args.append(request.provider)
        if request.configuration_tool == "":
            args.append("--configuration-tool")
            args.append(request.configuration_tool)
        if request.async:
            args.append("--async")
        if len(request.extra) > 0:
            args.append("--extra")
        for key, value in request.extra.items():
            args.append(key+'='+value)


def serve():
    request = ClouniRequest(extra={'key1':'value1', 'key2':'value2'}, provider='qwerty', template_file_content="qwe", cluster_name='asd')
    ClouniServicer().Clouni(request, 1)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    api_pb2_grpc.add_ClouniServicer_to_server(
        ClouniServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
