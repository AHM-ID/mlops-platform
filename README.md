# MLOps Churn Prediction Platform

Production-grade MLOps system for churn prediction using FastAPI, MLflow, PostgreSQL, Redis, Celery, Prometheus, Grafana, Loki, and Nginx. The system supports model training, experiment tracking, model registry, asynchronous retraining, observability, and containerized deployment.

---

# Architecture

```
Client → Nginx → FastAPI API → MLflow → PostgreSQL
                  ↓
Redis → Celery Worker (Retraining)
                  ↓
S3-compatible storage (Garage)
                  ↓
Prometheus + Grafana + Loki (Observability)
```

---

# Features

* Machine learning pipeline for churn prediction
* Feature engineering and preprocessing pipeline
* Model training with MLflow tracking and registry
* Hyperparameter optimization using Optuna
* FastAPI inference service
* Asynchronous retraining using Celery
* PostgreSQL backend for MLflow metadata
* S3-compatible artifact storage (Garage)
* Monitoring stack: Prometheus, Grafana, Loki
* Nginx reverse proxy for routing
* Fully containerized with Docker Compose / Podman Compose

---

# Services

| Service    | Description                    | Port |
| ---------- | ------------------------------ | ---- |
| Nginx      | Reverse proxy                  | 80   |
| API        | FastAPI inference service      | 8000 |
| MLflow     | Experiment tracking UI         | 5000 |
| Prometheus | Metrics collection             | 9090 |
| Grafana    | Dashboards and visualization   | 3000 |
| Loki       | Log aggregation                | 3100 |
| Redis      | Message broker for Celery      | 6379 |
| PostgreSQL | MLflow metadata store          | 5432 |
| Garage     | S3-compatible artifact storage | 3900 |

---

# Requirements

* Docker or Podman
* Docker Compose or Podman Compose
* Git

---

# Setup

## 1. Clone repository

```bash
git clone https://hamgit.ir/mr.amirhosseinmaleki/mlops-platform
cd mlops-platform
```

## 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
POSTGRES_DB=mlops
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin

MLFLOW_S3_ENDPOINT_URL=http://garage:3900
AWS_ACCESS_KEY_ID=admin
AWS_SECRET_ACCESS_KEY=password

MLFLOW_TRACKING_URI=http://mlflow:5000
REDIS_URL=redis://redis:6379/0

GRAFANA_ADMIN_PASSWORD=admin

DOCKER_REGISTRY=docker.arvancloud.ir
PIP_INDEX_URL=https://pypi.devneeds.ir/simple/
PIP_TRUSTED_HOST=pypi.devneeds.ir
```

---

## 3. Start system

### Docker Compose

```bash
docker compose up --build -d
```

### Podman Compose

```bash
podman-compose --env-file .env up -d --build
```

---

# API Usage

## Health Check

```bash
curl http://localhost/api/health
```

## Prediction

```bash
curl -X POST http://localhost/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "gender":"Male",
    "SeniorCitizen":0,
    "Partner":"No",
    "Dependents":"No",
    "tenure":1,
    "PhoneService":"Yes",
    "MultipleLines":"No",
    "InternetService":"DSL",
    "OnlineSecurity":"No",
    "OnlineBackup":"Yes",
    "DeviceProtection":"No",
    "TechSupport":"No",
    "StreamingTV":"No",
    "StreamingMovies":"No",
    "Contract":"Month-to-month",
    "PaperlessBilling":"Yes",
    "PaymentMethod":"Electronic check",
    "MonthlyCharges":29.85,
    "TotalCharges":29.85
  }'
```

## Metrics

```bash
curl http://localhost/api/metrics
```

---

# Retraining

## Trigger manual retraining

```bash
docker exec -it <worker_container> \
python -c "from worker.celery_app import retrain; retrain.delay()"
```

## Notes

* Requires Redis to be running
* Celery worker must be active
* Can be scheduled using Celery Beat

---

# MLflow

* UI: [http://localhost/mlflow](http://localhost/mlflow)
* Backend: PostgreSQL
* Artifacts: Garage S3-compatible storage
* Model registry enabled

---

# Monitoring

## Prometheus

* Scrapes `/metrics` from API and MLflow
* Available at [http://localhost:9090](http://localhost:9090)

## Grafana

* URL: [http://localhost:3000](http://localhost:3000)
* Default credentials: admin / admin
* Datasources: Prometheus, Loki

## Loki

* Logs collected via Promtail
* Query example:

```
{service="api"} |= "prediction"
```

---

# Logging

* Structured JSON logging enabled
* Collected via Promtail
* Stored in Loki
* Queryable via Grafana

---

# Deployment Notes

## Production Considerations

* Enable HTTPS via reverse proxy
* Configure persistent volumes for all services
* Set proper retention policies for Loki
* Secure Grafana credentials
* Restrict MLflow access in production

---

## Kubernetes (Experimental)

```bash
kompose convert -f docker-compose.yml
kubectl apply -f .
```

Note: Requires manual adjustment for ingress, secrets, and persistent storage.

---

# Limitations

* MLflow metrics endpoint may not be available by default
* Prometheus node exporter not included
* Kubernetes configuration is not production-ready
* Garage requires correct S3-compatible configuration

---

# Future Improvements

* CI/CD pipeline integration
* Kubernetes Helm chart
* Model drift detection
* Alertmanager integration
* Distributed training support
* Feature store integration
