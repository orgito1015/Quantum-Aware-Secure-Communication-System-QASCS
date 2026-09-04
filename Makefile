.PHONY: install setup dev certs server client web lint typecheck test precommit clean

# Install package in editable mode with dev dependencies
install:
	pip install -e ".[dev]"

# First-time setup: install deps + package
setup: install

# Alias for setup (same as setup)
dev: install

certs:
	qasccs gen-certs --out qasccs/secure_channel/certs

server:
	qasccs server --host 127.0.0.1 --port 8443

client:
	qasccs client --host 127.0.0.1 --port 8443 --data-lifetime-years 10 --data-classification high

# Requires: pip install -e ".[web]"
web:
	qasccs web --host 127.0.0.1 --port 8000

lint:
	ruff check .

typecheck:
	mypy qasccs

# Run tests (requires package to be installed first)
test:
	@pip show qasccs >/dev/null 2>&1 || (echo "Error: qasccs package not installed. Run 'make install' first." >&2 && exit 1)
	pytest -q

precommit:
	pre-commit install

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
