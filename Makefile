# ============================================
# MLOps Platform Makefile
# Works on Linux (Podman) and Windows (Docker)
# ============================================

.PHONY: help up down down-v restart logs ps build fix clean

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    COMPOSE_CMD = podman-compose --env-file .env
    WAIT_CMD = sleep
else
    COMPOSE_CMD = docker compose --env-file .env
    WAIT_CMD = timeout /t
endif

help:
	@echo "Commands:"
	@echo "  make up               - Full startup"
	@echo "  make down             - Stop all services"
	@echo "  make down-v           - Stop all services and remove volumes"
	@echo "  make restart          - Restart API and Nginx"
	@echo "  make logs [SERVICE]   - Show logs (usage: make logs SERVICE=api)"
	@echo "  make ps               - Show service status"

up:
	@echo "Starting MLOps Platform..."
	$(COMPOSE_CMD) up -d postgres redis garage
	@echo "Waiting for databases..."
	$(WAIT_CMD) 15
	@echo "Setting up Garage..."
	$(COMPOSE_CMD) run --rm garage-setup
	@echo "Training initial model..."
	$(COMPOSE_CMD) run --rm trainer
	$(WAIT_CMD) 5
	@echo "Building and starting all remaining services..."
	$(COMPOSE_CMD) up -d --build
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