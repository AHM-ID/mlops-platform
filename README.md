
# MLOps Churn Prediction Platform

This project is a lightweight MLOps pipeline for customer churn prediction.

It includes:
- Model training (RandomForest + Optuna)
- Feature engineering pipeline
- FastAPI inference service
- Basic metrics tracking
- Local file-based model storage

---

# Requirements

- Python 3.11+
- pip
- virtualenv (recommended)

---

# Setup

## 1. Create environment

```bash
python3 -m venv .venv
source .venv/bin/activate
````

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

# Training model

Run training pipeline:

```bash
python trainer/train.py
```

This will generate:

* model.pkl
* columns.pkl

---

# Run API server

Start FastAPI service:

```bash
uvicorn api.main:app --reload
```

Server runs at:

```
http://localhost:8000
```

---

# API Usage

## Health check

```bash
GET /health
```

---

# Notes

* This mode does NOT use Docker
* This mode does NOT use MLflow server
* This mode stores models locally
* Production version uses MLflow + Garage + Kubernetes

---

# Next Steps

* Add MLflow tracking server
* Replace local model with registry model
* Add Docker deployment
* Add monitoring (Prometheus + Grafana)
* Deploy on K3s cluster