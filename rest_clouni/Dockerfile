FROM python:3.6.13-slim
LABEL maintainer="ISP RAS"
WORKDIR /app/
RUN apt update &&\
    apt install git -y
RUN git clone https://github.com/bura2017/tosca-parser.git &&\
    cd tosca-parser &&\
    git checkout develop &&\
    pip install -U -r requirements.txt &&\
    python setup.py install
RUN git clone https://github.com/AlexanderMishutkin/clouni.git &&\
    cd clouni &&\
    git checkout http-api &&\
    pip install -U -r requirements.txt &&\
    pip install -U -r requirements-rest.txt &&\
    python setup.py install
RUN cd clouni && mkdir artifacts
ENV FLASK_APP /app/clouni/rest_clouni/app.py
WORKDIR /app/clouni/
EXPOSE 5000
CMD [ "python", "-m" , "flask", "run", "--host=0.0.0.0"]
