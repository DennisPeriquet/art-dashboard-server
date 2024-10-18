# Define variables
OPENSHIFT=$(HOME)/tmp/art-ui
GIT_TOKEN_FILE=$(OPENSHIFT)/.git/git_token
NETWORK_NAME=art-dashboard-network
MARIADB_CONTAINER_NAME=mariadb
MARIADB_IMAGE=docker.io/library/mariadb:10.6.14
MARIADB_ROOT_PASSWORD=secret
MARIADB_DATABASE=doozer_build

ART_DASHBOARD_SERVER_DIR=$(OPENSHIFT)/art-dashboard-server
ART_TOOLS_DIR=$(OPENSHIFT)/art-tools
TEST_URL=http://localhost:8080/api/v1/test

# Build the development environment images
.PHONY: build-dev
build-dev:
	podman build -f Dockerfile.base -t art-dash-server:base --build-arg USERNAME=$(USER) --build-arg USER_UID=1000 .
	podman build -f Dockerfile.update -t art-dash-server:latest --build-arg USERNAME=$(USER) --build-arg USER_UID=1000 .

# Default target for setting up the environment
.PHONY: setup-dev-env
setup-dev-env: check-network check-mariadb clone-repos

# Check if the Podman network exists, create if it doesn't
.PHONY: check-network
check-network:
	@if ! podman network exists $(NETWORK_NAME); then \
		echo "Creating Podman network $(NETWORK_NAME)"; \
		podman network create $(NETWORK_NAME); \
	else \
		echo "Podman network $(NETWORK_NAME) already exists"; \
	fi

# Check if the MariaDB container is running, start if it's not
.PHONY: check-mariadb
check-mariadb:
	@if ! podman ps -a --format "{{.Names}}" | grep -w $(MARIADB_CONTAINER_NAME) > /dev/null; then \
		echo "Starting MariaDB container"; \
		podman run --net $(NETWORK_NAME) --name $(MARIADB_CONTAINER_NAME) \
			-e MARIADB_ROOT_PASSWORD=$(MARIADB_ROOT_PASSWORD) \
			-e MARIADB_DATABASE=$(MARIADB_DATABASE) \
			-d $(MARIADB_IMAGE); \
	else \
		echo "MariaDB container $(MARIADB_CONTAINER_NAME) already running"; \
	fi

# Clone repositories if they don't exist
.PHONY: clone-repos
clone-repos:
	@if [ ! -d $(ART_DASHBOARD_SERVER_DIR) ]; then \
		echo "Cloning art-dashboard-server"; \
		git clone https://github.com/openshift-eng/art-dashboard-server.git $(ART_DASHBOARD_SERVER_DIR); \
	fi
	@if [ ! -d $(ART_TOOLS_DIR) ]; then \
		echo "Cloning art-tools"; \
		git clone https://github.com/openshift-eng/art-tools.git $(ART_TOOLS_DIR); \
	fi

# Target to run the development environment
.PHONY: run-dev
run-dev:
	@if [ ! -f $(GIT_TOKEN_FILE) ]; then \
		echo "Error: GitHub token file not found."; \
		exit 1; \
	fi
	@GITHUB_TOKEN=$$(cat $(GIT_TOKEN_FILE)) && \
	podman run -it --name dj1 --rm -p 8080:8080 -p 5678:5678 --net $(NETWORK_NAME) \
	-v "$(ART_TOOLS_DIR)/doozer/":/workspaces/doozer/:cached,z \
	-v "$(ART_TOOLS_DIR)/elliott/":/workspaces/elliott/:cached,z \
	-v $(HOME)/.ssh:/home/$(USER)/.ssh:ro,cached,z \
	-v $(OPENSHIFT)/.docker/config.json:/home/$(USER)/.docker/config.json:ro,cached,z \
	-v $(OPENSHIFT)/.git/.gitconfig:/home/$(USER)/.gitconfig:ro,cached,z \
	-e RUN_ENV=development \
	-e GITHUB_PERSONAL_ACCESS_TOKEN=$$GITHUB_TOKEN \
	art-dash-server:latest

# Test if the server is running by checking the response of curl to the API
.PHONY: dev-test
dev-test:
	@curl -s -o /dev/null -w "%{http_code}" $(TEST_URL) | grep -q 200 && \
		echo "dev environment is working" || echo "dev environment is not working"

# Clean up development environment by stopping and removing containers and network
.PHONY: clean-dev
clean-dev:
	@if podman ps -a --format "{{.Names}}" | grep -w $(MARIADB_CONTAINER_NAME) > /dev/null; then \
		echo "Stopping and removing MariaDB container"; \
		podman stop $(MARIADB_CONTAINER_NAME) && podman rm $(MARIADB_CONTAINER_NAME); \
	fi
	@if podman network exists $(NETWORK_NAME); then \
		echo "Removing Podman network $(NETWORK_NAME)"; \
		podman network rm $(NETWORK_NAME); \
	fi
