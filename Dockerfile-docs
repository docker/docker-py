FROM python:3.5

ARG uid=1000
ARG gid=1000

RUN addgroup --gid $gid sphinx \
 && useradd --uid $uid --gid $gid -M sphinx

WORKDIR /src
COPY requirements.txt docs-requirements.txt ./
RUN pip install -r requirements.txt -r docs-requirements.txt

USER sphinx
