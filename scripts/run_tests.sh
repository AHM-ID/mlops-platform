#!/bin/bash

echo "========================================="
echo "MLOps Platform Test Suite"
echo "========================================="

cd "$(dirname "$0")/.."

export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create temporary Prometheus metrics directory for testing
export PROMETHEUS_MULTIPROC_DIR="/tmp/prometheus-metrics-$$"
mkdir -p "$PROMETHEUS_MULTIPROC_DIR"

# Clean up on exit
trap "rm -rf $PROMETHEUS_MULTIPROC_DIR" EXIT

echo "Running all tests..."

pytest tests/ \
    -v \
    --tb=short \
    --disable-warnings \
    --cov=api \
    --cov=shared \
    --cov=trainer \
    --cov=worker \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage_report

TEST_EXIT_CODE=$?

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed. Check output above."
fi

echo "Coverage report: tests/coverage_report/index.html"
echo "========================================="

exit $TEST_EXIT_CODE