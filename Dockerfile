ARG OPENJDK_TAG=8u302
FROM openjdk:${OPENJDK_TAG}

WORKDIR /app

RUN apt-get update -qq\
 && apt-get install --no-install-recommends -y \
  build-essential \
  python3 \
  python3-setuptools \
  python3-dev \
  python3-pip


ARG SCALA_VERSION
ENV SCALA_VERSION ${SCALA_VERSION:-2.13.1}

RUN \ 
   wget https://downloads.lightbend.com/scala/$SCALA_VERSION/scala-$SCALA_VERSION.deb

# hack hack hack
RUN dpkg -i scala-$SCALA_VERSION.deb ; exit 0
RUN apt install -fy

RUN apt-get clean

WORKDIR /app/

COPY geonorm-assembly-0.1.0-SNAPSHOT.jar /app/
COPY requirements.txt /app/

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

RUN python3 -m spacy download en_core_web_trf

COPY runGeoParse.sh /app/
COPY NER.py /app/

CMD python3 NER.py ./example
