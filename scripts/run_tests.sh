#!/usr/bin/env bash
# Run unit tests without starting the MLOps platform stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export TESTING=true
export RATE_LIMIT_ENABLED=false
export PROMETHEUS_MULTIPROC_DIR="${PROMETHEUS_MULTIPROC_DIR:-/tmp/prometheus-test}"
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"

PYTEST_ARGS=("$@")
if [ "${#PYTEST_ARGS[@]}" -eq 0 ]; then
  PYTEST_ARGS=(tests/ -v -m "not integration" --tb=short)
fi

if command -v pytest >/dev/null 2>&1; then
  echo "Running unit tests locally (pytest)..."
  exec pytest "${PYTEST_ARGS[@]}"
fi

if command -v docker >/dev/null 2>&1; then
  echo "Running unit tests in Docker (no platform stack required)..."
  docker compose -f docker-compose.test.yml build unit-test
  exec docker compose -f docker-compose.test.yml run --rm unit-test \
    sh -c "mkdir -p /tmp/prometheus-test && pytest ${PYTEST_ARGS[*]}"
fi

echo "ERROR: install pytest or Docker to run tests." >&2
exit 1
