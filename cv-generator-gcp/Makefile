.PHONY: test test-unit test-integration test-all test-supabase test-parser test-frontend

# Default test target - runs unit tests only
test: test-unit

# Run unit tests
test-unit:
	pytest tests/unit/ -v

# Run integration tests
test-integration:
	pytest tests/integration/ -v

# Run Supabase integration tests
test-supabase:
	RUN_LIVE_SUPABASE_TESTS=1 pytest tests/integration/test_supabase_integration.py -v

# Run Parser service integration tests
test-parser:
	RUN_LIVE_PARSER_TESTS=1 pytest tests/integration/test_parser_service.py -v

# Run Frontend contract tests
test-frontend:
	RUN_LIVE_FRONTEND_TESTS=1 pytest tests/integration/test_frontend_contracts.py -v

# Run all tests
test-all:
	pytest tests/ -v

# Run tests with coverage report
test-coverage:
	pytest --cov=. tests/ --cov-report=term-missing

# Clean up Python cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

# Set up test environment
setup-test-env:
	pip install -r requirements.txt 