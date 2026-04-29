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

RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x scripts/wait.sh

CMD ["python", "trainer/train.py"]