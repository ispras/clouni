from toscatranslator.api_pb2 import ClouniResponse, ClouniRequest
import toscatranslator.api_pb2_grpc as api_pb2_grpc
import toscatranslator.shell as shell
from toscaparser.common.exception import ValidationError
from concurrent import futures
import logging
import grpc

class ClouniServicer(api_pb2_grpc.ClouniServicer):

    def Clouni(self, request, context):
        args = _RequestParse(request)
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

# print(dir(ClouniResponse()))
# c = ClouniResponse()
# c.status = ClouniResponse.Status.OK
# c.error = " "
# c.content = " "
# print((c))
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    api_pb2_grpc.add_ClouniServicer_to_server(
        ClouniServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
