ARG DOCKER_REGISTRY
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST

FROM ${DOCKER_REGISTRY}/python:3.11.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install \
    --trusted-host ${PIP_TRUSTED_HOST} \
    -i ${PIP_INDEX_URL} \
    -r requirements.txt

COPY . .

CMD ["python", "trainer/train.py"]