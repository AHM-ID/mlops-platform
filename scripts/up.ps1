# Same flow as Makefile target "up" — use on Windows when "make" is not installed.
# Run from repo root:  .\scripts\up.ps1
# Or from anywhere:   powershell -File path\to\scripts\up.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Invoke-Compose {
    & docker compose --env-file .env @args
}

Write-Host "Building base images (garage-setup, trainer, api, worker)..."
Invoke-Compose build garage-setup trainer api worker

Write-Host "Starting postgres, redis, garage..."
Invoke-Compose up -d postgres redis garage
Start-Sleep -Seconds 10

Write-Host "Garage setup..."
Invoke-Compose run --rm garage-setup

Write-Host "Starting mlflow..."
Invoke-Compose up -d mlflow
Start-Sleep -Seconds 30

Write-Host "Starting fluent-bit, loki..."
Invoke-Compose up -d fluent-bit loki
Start-Sleep -Seconds 10

Write-Host "Training initial model (trainer)..."
Invoke-Compose run --rm trainer
Start-Sleep -Seconds 5

Write-Host "Starting api, worker, prometheus, grafana, nginx..."
Invoke-Compose up -d api worker prometheus grafana nginx
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "MLOps Platform is ready"
Write-Host "  API docs:    http://localhost:8080/api/docs"
Write-Host "  Grafana:     http://localhost:8080/grafana/"
Write-Host "  Prometheus:  http://localhost:8080/prometheus/"
Write-Host "  MLflow:      http://localhost:8080/mlflow/"
