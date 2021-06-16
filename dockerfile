FROM python:3.6.13-slim
LABEL maintainer="ISP RAS"
WORKDIR /app/
RUN apt-get update &&\
    apt-get install wget unzip -y &&\
    apt-get clean
RUN wget --no-check-certificate https://github.com/bura2017/tosca-parser/archive/refs/heads/develop.zip -O tosca-parser-develop.zip &&\
    unzip tosca-parser-develop.zip &&\
    cd tosca-parser-develop &&\
    pip install -U -r requirements.txt &&\
    PBR_VERSION=5.4.5 python setup.py install
RUN wget --no-check-certificate https://github.com/ispras/clouni/archive/refs/heads/grpc.zip -O clouni-master.zip &&\
    unzip clouni-master.zip &&\
    cd clouni-grpc &&\
    pip install -U -r requirements.txt &&\
    pip install -U -r requirements-grpc.txt &&\
    PBR_VERSION=5.4.5 python setup.py install
RUN rm -r clouni-grpc tosca-parser-develop
EXPOSE 50051
ENTRYPOINT clouni-server --host 0.0.0.0 --foreground
