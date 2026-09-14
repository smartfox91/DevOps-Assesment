# Run Local Verification Harness
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Running respond.io DevOps Local Verification Suite       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$env:AWS_ACCESS_KEY_ID = "test"
$env:AWS_SECRET_ACCESS_KEY = "test"
$env:AWS_DEFAULT_REGION = "us-east-1"
$env:FLOCI_ENDPOINT = "http://localhost:4566"

$PYTHON_CMD = "python"
if (Test-Path ".venv\Scripts\python.exe") {
    $PYTHON_CMD = ".\.venv\Scripts\python.exe"
}

# 1. Run Unit Tests
Write-Host "`n[Step 1/2] Executing Unit Tests..." -ForegroundColor Yellow
& $PYTHON_CMD -m unittest tests/test_handler.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Unit tests failed!" -ForegroundColor Red
    exit 1
}

# 2. Run Floci End-to-End Test Suite
Write-Host "`n[Step 2/2] Executing Floci End-to-End Simulation..." -ForegroundColor Yellow
& $PYTHON_CMD scripts/verify_floci.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Floci verification failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nAll verification checks succeeded!" -ForegroundColor Green

