# Run unit tests without starting the MLOps platform stack.
# Prefers local pytest when available; otherwise uses docker-compose.test.yml.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:TESTING = "true"
$env:RATE_LIMIT_ENABLED = "false"
if (-not $env:PROMETHEUS_MULTIPROC_DIR) {
    $env:PROMETHEUS_MULTIPROC_DIR = Join-Path $env:TEMP "prometheus-test"
}
New-Item -ItemType Directory -Force -Path $env:PROMETHEUS_MULTIPROC_DIR | Out-Null

$pytestArgs = @("tests/", "-v", "-m", "not integration", "--tb=short")
if ($args.Count -gt 0) {
    $pytestArgs = $args
}

$pytestCmd = Get-Command pytest -ErrorAction SilentlyContinue
if ($pytestCmd) {
    Write-Host "Running unit tests locally (pytest)..." -ForegroundColor Cyan
    & pytest @pytestArgs
    exit $LASTEXITCODE
}

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Error "Neither pytest nor docker found. Install Python deps or Docker Desktop."
}

Write-Host "Running unit tests in Docker (no platform stack required)..." -ForegroundColor Cyan
docker compose -f docker-compose.test.yml build unit-test
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
docker compose -f docker-compose.test.yml run --rm unit-test @pytestArgs
exit $LASTEXITCODE
