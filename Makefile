PROJECT_NAME ?= slc-stock
MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_PATH := $(shell dirname $(MAKEFILE_PATH))
TEST_PATH := $(PROJECT_PATH)/tests/functional
IMAGE_TEST ?= $(PROJECT_NAME)-test
PYTEST_ARGS ?=

# Test run: interactive (TTY attached, excludes .env)
define docker_run_test
	docker run -u $$(id -u):$$(id -g) -e USER=$$USER --rm -it \
		-v $(PROJECT_PATH):/app \
		-v /dev/null:/app/.env:ro \
		-w /app $(1)
endef

# Test run: batch (TTY for colour, excludes .env)
define docker_run_test_batch
	docker run -u $$(id -u):$$(id -g) -e USER=$$USER --rm -t \
		-v $(PROJECT_PATH):/app \
		-v /dev/null:/app/.env:ro \
		-w /app $(1)
endef

# Test run: no-TTY (CI/agent mode, excludes .env)
define docker_run_test_notty
	docker run -u $$(id -u):$$(id -g) -e USER=$$USER --rm \
		-v $(PROJECT_PATH):/app \
		-v /dev/null:/app/.env:ro \
		-w /app $(1)
endef

.PHONY: banner help serve unittest test-image test test-notty test-shell clean

banner:
	@echo "§ slc-stock"

help: banner
	@echo ""
	@echo "Targets:"
	@echo "  serve      - Run the Flask server on port 8080"
	@echo "  unittest   - Run unit/integration tests locally (fast, no Docker)"
	@echo "  test-image - Build the Docker test image"
	@echo "  test       - Run functional tests (TTY attached)"
	@echo "  test-notty - Run functional tests (no TTY, for CI/agents)"
	@echo "  test-shell - Open a shell in the test container"
	@echo "  clean      - Remove Docker images and tidy up"
	@echo ""
	@echo "Variables:"
	@echo "  PYTEST_ARGS - Extra args passed to pytest (e.g. -k test_chart)"

serve: banner
	python -m slc_stock.app

unittest: banner
	pytest tests/ -v --ignore=tests/functional

test-image: banner
	docker build -t $(IMAGE_TEST) -f $(TEST_PATH)/Dockerfile $(PROJECT_PATH)

test: banner test-image
	@$(call docker_run_test_batch,$(IMAGE_TEST)) pytest $(PYTEST_ARGS) tests/functional/

test-notty: banner test-image
	@$(call docker_run_test_notty,$(IMAGE_TEST)) pytest -v --tb=short $(PYTEST_ARGS) tests/functional/

test-shell: banner test-image
	@$(call docker_run_test,$(IMAGE_TEST)) /bin/bash

clean: banner
	@echo "Removing Docker images..."
	-@docker rmi $(IMAGE_TEST) 2>/dev/null || true
	@echo "Removing dangling images..."
	-@docker image prune -f 2>/dev/null || true
	@echo "Removing __pycache__ and .pytest_cache..."
	@find $(PROJECT_PATH) -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find $(PROJECT_PATH) -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."
