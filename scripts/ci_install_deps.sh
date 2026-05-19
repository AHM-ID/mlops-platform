#!/bin/sh
# GitLab CI: staged pip install via Liara PyPI mirror (see Liara docs).
# https://package-mirror.liara.ir/repository/pypi/simple
set -eu

unset PIP_INDEX_URL PIP_TRUSTED_HOST PIP_EXTRA_INDEX_URL || true
export PIP_CONFIG_FILE=/dev/null
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_PROGRESS_BAR=on
export PIP_DEFAULT_TIMEOUT=300

INDEX="${CI_PIP_INDEX:-https://package-mirror.liara.ir/repository/pypi/simple}"
TRUSTED="${CI_PIP_TRUSTED:-package-mirror.liara.ir}"

log() { echo ""; echo "=== [$(date -u +%H:%M:%S)] $* ==="; }

pip_install() {
  python -m pip install \
    --retries 5 \
    --trusted-host ${TRUSTED} \
    -i "${INDEX}" \
    "$@"
}

log "Using Liara PyPI mirror: ${INDEX}"

log "1/4 — pytest toolchain"
pip_install \
  pytest pytest-cov pytest-mock pytest-asyncio \
  python-json-logger==2.0.7 psutil python-multipart

log "2/4 — API / data core"
pip_install \
  fastapi uvicorn pandas "numpy<2" "scikit-learn==1.3.2" joblib redis celery \
  prometheus-client "psycopg2-binary==2.9.12"

log "3/4 — MLflow + Optuna (large downloads)"
pip_install "mlflow==2.9.2" "optuna==3.5.0" boto3

log "4/4 — Evidently (largest; may take several minutes)"
pip_install "evidently==0.4.20"

log "All dependencies installed from Liara mirror"
