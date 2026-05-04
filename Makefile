# ============================================
# MLOps Platform Makefile
# Works on Linux (Podman) and Windows (Docker)
# ============================================

.PHONY: help build-base up down down-v restart logs ps

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    COMPOSE_CMD = podman-compose --env-file .env
    WAIT_CMD = sleep
else
    COMPOSE_CMD = docker compose --env-file .env
    WAIT_CMD = timeout /t
endif

include .env
export

help:
	@echo "Commands:"
	@echo "  make build-base       - Build base image with proper args"
	@echo "  make up               - Full startup"
	@echo "  make down             - Stop all services"
	@echo "  make down-v           - Stop all services and remove volumes"
	@echo "  make restart          - Restart API and Nginx"
	@echo "  make logs [SERVICE]   - Show logs (usage: make logs SERVICE=api)"
	@echo "  make ps               - Show service status"

build-base:
	@echo "Building base image with registry args..."
	podman build \
		--build-arg DOCKER_REGISTRY=${DOCKER_REGISTRY} \
		--build-arg PIP_INDEX_URL=${PIP_INDEX_URL} \
		--build-arg PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
		-t mlops-platform-base:latest .

up: build-base
	@echo "Starting MLOps Platform..."
	$(COMPOSE_CMD) up -d postgres redis garage
	@echo "Waiting for databases..."
	$(WAIT_CMD) 10
	@echo "Setting up Garage..."
	$(COMPOSE_CMD) run --rm garage-setup
	$(COMPOSE_CMD) up -d mlflow
	@echo "Waiting for mlflow..."
	$(WAIT_CMD) 40
	@echo "Training initial model..."
	$(COMPOSE_CMD) run --rm trainer
	$(WAIT_CMD) 5
	@echo "Starting all remaining services..."
	$(COMPOSE_CMD) up -d api worker prometheus grafana loki fluent-bit nginx
	$(WAIT_CMD) 5
	@echo "MLOps Platform is ready"
	@echo "API docs: http://localhost:8080/api/docs"
	@echo "Grafana: http://localhost:8080/grafana"
	@echo "Prometheus: http://localhost:8080/prometheus"
	@echo "Mlflow: http://localhost:8080/mlflow"

down:
	@echo "Stopping all services..."
	$(COMPOSE_CMD) down
	@echo "All services stopped"

down-v:
	@echo "Stopping all services and removing volumes..."
	$(COMPOSE_CMD) down -v
	@echo "All services stopped and volumes removed"

restart:
	@echo "Restarting API..."
	$(COMPOSE_CMD) restart api
	$(WAIT_CMD) 5
	@echo "Restarting Nginx..."
	$(COMPOSE_CMD) restart nginx
	@echo "API and Nginx restarted"

logs:
ifeq ($(SERVICE),)
	$(COMPOSE_CMD) logs -f --tail=100
else
	$(COMPOSE_CMD) logs -f --tail=100 $(SERVICE)
endif

ps:
	$(COMPOSE_CMD) ps