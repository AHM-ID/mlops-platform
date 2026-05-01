ARG DOCKER_REGISTRY
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST

FROM ${DOCKER_REGISTRY}/python:3.11.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y netcat-openbsd curl && rm -rf /var/lib/apt/lists/*

# Download Garage binary to use as a CLI client
RUN curl -L https://garagehq.deuxfleurs.fr/_releases/v0.8.2/x86_64-unknown-linux-musl/garage -o /usr/local/bin/garage && \
    chmod +x /usr/local/bin/garage

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --trusted-host ${PIP_TRUSTED_HOST} -i ${PIP_INDEX_URL} -r requirements.txt

COPY . .
RUN chmod +x scripts/*.sh

CMD ["python", "trainer/train.py"]