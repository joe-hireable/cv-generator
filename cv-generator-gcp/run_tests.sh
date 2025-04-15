#!/bin/bash

# Set environment variables for testing
export PROJECT_ID="test-project"
export STORAGE_BUCKET_NAME="test-bucket"
export PROFILE="profile.json"

# Run unit tests
echo "Running unit tests..."
python -m pytest tests/unit -v

# Run integration tests
echo "Running integration tests..."
python -m pytest tests/integration -v

# Run all tests with coverage
echo "Running all tests with coverage..."
python -m pytest --cov=. --cov-report=term-missing 