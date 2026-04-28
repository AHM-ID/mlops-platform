# MLOps Churn Prediction Platform (Production Ready)

Production-grade MLOps pipeline with Docker, MLflow, Prometheus, Grafana, Loki, and Nginx.

---

## Features

- Model training (RandomForest + Optuna) with MLflow tracking
- Feature engineering pipeline
- FastAPI inference service with Prometheus metrics
- MLflow model registry (PostgreSQL + Garage S3)
- Celery worker for async retraining
- Monitoring (Prometheus + Grafana + Loki)
- Nginx reverse proxy
- Full Docker Compose orchestration

---

## Quick Start

```bash
# Clone and enter project
git clone https://hamgit.ir/mr.amirhosseinmaleki/mlops-platform
cd mlops-platform

# Make wait script executable
chmod +x scripts/wait.sh

# Start all services
docker-compose up --build
```

---

## Services & Ports

| Service    | Port | URL                     |
| ---------- | ---- | ----------------------- |
| Nginx      | 80   | http://localhost        |
| API        | 8000 | http://localhost/api    |
| MLflow UI  | 5000 | http://localhost/mlflow |
| Prometheus | 9090 | http://localhost:9090   |
| Grafana    | 3000 | http://localhost:3000   |
| Loki       | 3100 | http://localhost:3100   |

Default Grafana: `admin` / `admin` (set via `.env`)

---

## API Usage

### Health check
```bash
curl http://localhost/api/health
```

### Prediction
```bash
curl -X POST http://localhost/api/predict \
  -H "Content-Type: application/json" \
  -d '{"gender":"Male","SeniorCitizen":0,"Partner":"No","Dependents":"No","tenure":1,"PhoneService":"Yes","MultipleLines":"No","InternetService":"DSL","OnlineSecurity":"No","OnlineBackup":"Yes","DeviceProtection":"No","TechSupport":"No","StreamingTV":"No","StreamingMovies":"No","Contract":"Month-to-month","PaperlessBilling":"Yes","PaymentMethod":"Electronic check","MonthlyCharges":29.85,"TotalCharges":29.85}'
```

### Metrics
```bash
curl http://localhost/api/metrics
```

---

## Retraining

Trigger async retraining via Celery (requires Redis):

```bash
docker exec -it <worker_container> python -c "from worker.celery_app import retrain; retrain.delay()"
```

Or schedule periodically using Celery Beat.

---

## Environment Variables

Copy `.env.example` to `.env` and adjust:

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
```

---

## Logging

All services output structured JSON logs (via `python-json-logger`). Loki + Promtail collect and index them. Query in Grafana using LogQL.

Example: `{service="api"} |= "prediction"`

---

## Monitoring

- Prometheus scrapes `/metrics` from API and MLflow.
- Pre-built Grafana dashboards can be imported (IDs: 1860 for Prometheus, 15141 for Loki).

---

## Production Deployment

For Kubernetes (k3s) deployment:

```bash
kompose convert -f docker-compose.yml
kubectl apply -f .
```

Or use Podman with `podman-compose up`.

---

## Notes

- Model is stored in MLflow registry (PostgreSQL metadata + Garage S3 artifacts).
- No local `model.pkl` or `columns.pkl` are used in production.
- Training runs once on startup; subsequent retraining via Celery.

---

## Next Steps

- Add MLflow autologging for deeper tracking.
- Implement CI/CD with GitLab Runner.
- Deploy on K3s with Helm.
- Add alerting (Alertmanager) for model drift.