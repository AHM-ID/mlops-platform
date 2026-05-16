# MLOps Churn Prediction Platform

Production-grade machine learning operations system for automated model training, real-time inference, asynchronous retraining, and comprehensive observability. The platform orchestrates the complete ML lifecycle within a containerized microservices architecture, ensuring reproducible deployments, versioned artifacts, and continuous model improvement.

## Architecture

The system follows a layered microservices pattern orchestrated via Docker Compose or Podman Compose:

![system architecture](./assets/pics/architecture.svg)

- **Edge Layer:** Nginx reverse proxy handling path-based routing, header forwarding, and WebSocket support.
- **Inference Layer:** Stateless FastAPI service for real-time predictions, feature caching, and metric exposure.
- **Async Processing:** Celery worker handling batch predictions and model retraining tasks.
- **Stateful Backends:** PostgreSQL (MLflow metadata), Redis (cache, broker, retrain queue), Garage (S3-compatible artifact storage), MLflow (tracking server).
- **Observability Stack:** Fluent-bit (async log collection) -> Loki (log storage) + Prometheus (metrics scraping) -> Grafana (unified visualization).

## Key Features

- **End-to-End ML Pipeline:** Automated data ingestion, feature engineering, missing value handling, and stratified 80/20 train-test splitting.
- **Hyperparameter Optimization:** Optuna-driven TPE sampling with 15 trials and 5-fold cross-validation, maximizing ROC-AUC.
- **Experiment Tracking & Registry:** MLflow integration for parameter logging, metric tracking, and versioned artifact storage (`model.pkl`, `columns.pkl`).
- **Conditional Model Promotion:** Automatic performance comparison (AUC, accuracy, F1) between newly trained models and the active Production version before stage transition.
- **High-Performance Inference:** FastAPI REST API with Pydantic validation, real-time single predictions, and asynchronous batch processing.
- **API Authentication & Authorization:** Role-based access control (admin, user, readonly) with API key authentication via `X-API-Key` header.
- **Rate Limiting:** Redis-backed sliding window rate limiting with role-based limits (admin: 1000/min, user: 100/min, readonly: 50/min, anonymous: 10/min).
- **Distributed Feature Caching:** Redis-backed caching with MD5 content hashing, configurable 3600s TTL, hit/miss tracking, and graceful degradation on Redis failure.
- **Intelligent Retraining Queue:** Automatic prediction logging to Redis, batch extraction for incremental training, CSV fallback, and auto-clear on successful promotion.
- **Comprehensive Observability:** Prometheus metrics scraping, structured JSON logging via async HTTP handler, Fluent-bit to Loki pipeline, and unified Grafana dashboards.
- **Production-Ready Deployment:** Nginx reverse proxy, cross-platform Docker/Podman support, automated health checks, persistent volumes, and `Makefile` orchestration.

## Technology Stack

| Category            | Technologies                                                                        |
| ------------------- | ----------------------------------------------------------------------------------- |
| API & Frameworks    | FastAPI, Uvicorn, Pydantic, Celery                                                  |
| Machine Learning    | scikit-learn, Optuna, MLflow, XGBoost, Pandas, NumPy                                |
| Storage & Databases | PostgreSQL (metadata), Redis (cache, broker, queue), Garage (S3-compatible storage) |
| Observability       | Prometheus, Grafana, Loki, Fluent-bit                                               |
| Infrastructure      | Nginx (reverse proxy), Docker/Podman Compose, GNU Make                              |

## Project Structure

```
mlops-platform/
├── api/                  # FastAPI application, routers, schemas, services
├── assets/pics/          # Architecture diagrams
├── data/                 # Customer churn dataset (churn.csv)
├── infra/                # Infrastructure configurations (Nginx, Prometheus, Loki, Fluent-bit, Garage)
├── scripts/              # Setup and utility scripts (garage-setup.sh, wait.sh)
├── shared/               # Shared modules (config, logging, feature_store, model_manager, retrain_queue, validator)
├── trainer/              # Training pipeline, feature engineering, optimization, evaluation
├── worker/               # Celery worker, batch predictor, task definitions
├── docker-compose.yml    # Service orchestration
├── Dockerfile            # Base image definition
├── Makefile              # Cross-platform build and lifecycle management
└── requirements.txt      # Python dependencies
```

## Prerequisites

- Linux or Windows host with Docker or Podman installed
- GNU Make
- Git
- Foundational knowledge of containerization, REST APIs, and environment configuration

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://hamgit.ir/mr.amirhosseinmaleki/mlops-platform
   cd mlops-platform
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` to define database credentials, S3 endpoints, registry mirrors, and service passwords.

3. **Initialize and start the platform:**
   ```bash
   make up
   ```
   This target automatically builds the base image, starts backing services, initializes Garage storage, trains the initial model, and launches the API, worker, and observability stack in the correct dependency order.

4. **Verify deployment:**
   ```bash
   make ps
   curl http://localhost:8080/api/health
   ```
   Access interactive API documentation at `http://localhost:8080/api/docs`

## Configuration

All system parameters are externalized through the `.env` file. Key variables include:

| Variable                                            | Purpose                             | Default/Sample                     |
| --------------------------------------------------- | ----------------------------------- | ---------------------------------- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database authentication             | `mlops`, `admin`, `admin`          |
| `MLFLOW_S3_ENDPOINT_URL`                            | Garage S3 endpoint                  | `http://garage:3900`               |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`        | Object storage credentials          | Auto-generated during setup        |
| `MLFLOW_TRACKING_URI`                               | Tracking server address             | `http://mlflow:5000`               |
| `REDIS_URL`                                         | Queue and cache connection string   | `redis://redis:6379/0`             |
| `GRAFANA_ADMIN_PASSWORD`                            | Dashboard login password            | Configurable in `.env`             |
| `DOCKER_REGISTRY`, `PIP_INDEX_URL`                  | Container image and package mirrors | Set for internal/external networks |

## API Usage

All endpoints are accessible via the Nginx reverse proxy at `http://localhost:8080`. Interactive documentation is available at `/api/docs`.

### Core Endpoints

| Method   | Path                                 | Description                                              |
| -------- | ------------------------------------ | -------------------------------------------------------- |
| `GET`    | `/api/health`                        | Verifies API status and backend connectivity             |
| `POST`   | `/api/predictions/single`            | Real-time churn prediction with caching and auto-logging |
| `POST`   | `/api/predictions/batch`             | Asynchronous batch prediction (up to 10,000 records)     |
| `GET`    | `/api/batch/{id}/status`             | Track batch job progress                                 |
| `GET`    | `/api/batch/{id}/results`            | Retrieve completed batch results and summary             |
| `GET`    | `/api/models/current`                | View production/staging models and version history       |
| `POST`   | `/api/models/deploy`                 | Manually promote a model version to target stage         |
| `GET`    | `/api/monitoring/metrics`            | Application metrics (request count, latency, error rate) |
| `GET`    | `/api/monitoring/metrics/prometheus` | Prometheus-compatible metrics endpoint                   |
| `GET`    | `/api/monitoring/health/system`      | System resource utilization and service connectivity     |
| `GET`    | `/api/monitoring/cache/stats`        | Feature cache hit/miss statistics                        |
| `DELETE` | `/api/monitoring/cache`              | Clear all cached features                                |
| `GET`    | `/api/retrain-queue/status`          | Check pending training data queue length                 |
| `DELETE` | `/api/retrain-queue/clear`           | Flush the retraining queue                               |
| `POST`   | `/api/retrain`                       | Trigger asynchronous model retraining                    |
| `GET`    | `/api/retrain/{task_id}/status`      | Monitor retraining task progress                         |

### Example Request

```bash
curl -X POST http://localhost:8080/api/predictions/single \
  -H "Content-Type: application/json" \
  -d '{
     "customer_id": "CUST001",
     "tenure": 24,
     "MonthlyCharges": 75.5,
     "TotalCharges": 1814.0,
     "Contract": "Two year",
     "InternetService": "Fiber optic",
     "PaymentMethod": "Electronic check"
  }'
```

### Example Response

```json
{
  "customer_id": "CUST001",
  "prediction": 0,
  "probability": 0.15,
  "confidence": 15.0,
  "model_version": "3"
}
```

## Model Training & Retraining Pipeline

1. **Initial Training:** Executed during platform startup. Loads `data/churn.csv`, performs one-hot encoding and missing value handling, runs Optuna hyperparameter optimization, trains a Random Forest classifier, evaluates metrics, and registers the model in MLflow.
2. **Conditional Promotion:** Newly trained models are automatically compared against the current Production version using AUC, accuracy, and F1 scores. Promotion to Production occurs only if the new model meets or exceeds baseline performance on at least one metric without degrading others.
3. **Asynchronous Retraining:** Triggered via `POST /api/retrain`. The Celery worker executes `train_from_redis.py`, which prioritizes labeled data from the Redis retrain queue. If the queue is empty or contains insufficient valid records, it falls back to the original CSV dataset.
4. **Data Collection & Loop:** Every successful inference is automatically appended to the Redis retrain queue. Labeled ground-truth data can be submitted manually via the API. The queue is cleared automatically upon successful model promotion to prevent stale data accumulation.

## Observability & Monitoring

- **Metrics Collection:** Prometheus scrapes application metrics every 15 seconds. Custom counters track total API requests, successful/failed requests, response durations, and active connections. Exposed at `/api/monitoring/metrics/prometheus`.
- **Log Aggregation:** Services emit structured JSON logs containing timestamps, severity levels, service identifiers, and request metadata. Fluent-bit collects these logs asynchronously via HTTP and forwards them to Loki.
- **Visualization:** Grafana provides pre-configured dashboards connected to Prometheus for time-series metrics and to Loki for LogQL-based log exploration. Dashboards are accessible via `/grafana/`.
- **System Health:** The `/api/monitoring/health/system` endpoint reports CPU, memory, disk utilization, and backend service connectivity status using `psutil` and direct connection probes.

## Deployment & Scaling

- **Orchestration:** Managed entirely through `docker-compose.yml` or `podman-compose`. The `Makefile` abstracts startup sequences, dependency ordering, and cross-platform compatibility.
- **Persistence:** Named volumes ensure data durability for PostgreSQL, Garage, Grafana, Loki, and Fluent-bit buffering.
- **Scaling:** The FastAPI API is stateless and can be horizontally scaled behind Nginx. Celery worker concurrency can be increased to handle higher retraining or batch prediction loads.
- **Network Routing:** Nginx handles path-based routing, WebSocket upgrades for Grafana, and header forwarding (`X-Real-IP`, `X-Forwarded-For`) for sub-path compatibility.

## Operational Notes

- The platform requires the `churn.csv` dataset to be present in the `./data/` directory.
- Garage S3 credentials are automatically generated and injected into the `.env` file during initial setup via `garage-setup.sh`.
- All sensitive credentials must be managed through environment variables. Hardcoded values are strictly prohibited.
- Container health checks automatically restart unhealthy services. Network discovery relies on container names within the `mlops-network` bridge.
- The platform is designed for seamless migration to Kubernetes or Docker Swarm with minimal configuration adjustments.
