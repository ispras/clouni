FROM python:3.6.13
LABEL maintainer="gkgim@yandex.ru"
WORKDIR /app/
RUN git clone https://github.com/bura2017/tosca-parser.git &&\
    cd tosca-parser &&\
    git checkout develop &&\
    pip install -r requirements.txt &&\
    python setup.py install
RUN pwd && ls -la
RUN git clone https://github.com/ispras/clouni.git &&\
    cd clouni &&\
    git checkout master &&\
    pip install -r requirements.txt
    #python setup.py install

RUN apt -y update && apt -y upgrade && apt install net-tools
RUN pip install protobuf &&\
    pip install grpcio &&\
    pip install grpcio-tools
WORKDIR /app/clouni
RUN python setup.py install
EXPOSE 50051
ENTRYPOINT clouni-server --host 0.0.0.0
