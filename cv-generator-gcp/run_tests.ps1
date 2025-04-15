# Set environment variables for testing
$env:PROJECT_ID = "test-project"
$env:STORAGE_BUCKET_NAME = "test-bucket"
$env:PROFILE = "profile.json"

# Run unit tests
Write-Host "Running unit tests..." -ForegroundColor Green
python -m pytest tests/unit -v

# Run integration tests
Write-Host "Running integration tests..." -ForegroundColor Green
python -m pytest tests/integration -v

# Run all tests with coverage
Write-Host "Running all tests with coverage..." -ForegroundColor Green
python -m pytest --cov=. --cov-report=term-missing 