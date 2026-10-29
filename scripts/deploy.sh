#!/bin/bash

# =====================================================
# RiskOptimizer Deployment Script
# =====================================================
# This script provides a simple, container-based deployment
# mechanism using Docker Compose.
#
# PREREQUISITE: Docker and Docker Compose must be installed.
# =====================================================

set -euo pipefail

PROJECT_ROOT=$(dirname "$0")
cd "$PROJECT_ROOT"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting RiskOptimizer deployment process...${NC}"

# --- Helper Functions ---
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: Required command '$1' is not installed. Please install it to proceed with deployment.${NC}"
        exit 1
    fi
}

# --- 1. Check Prerequisites ---
echo_step "Checking prerequisites (Docker and Docker Compose)"
check_command docker
check_command docker-compose

# --- 2. Build Docker Images ---
echo_step "Building Docker images"
# Assuming a docker-compose.yml file exists in the root
if [ -f "docker-compose.yml" ]; then
    docker-compose build --no-cache
    echo -e "${GREEN}Docker images built successfully.${NC}"
else
    echo -e "${RED}Error: docker-compose.yml not found. Cannot build images.${NC}"
    exit 1
fi

# --- 3. Deploy/Run Containers ---
echo_step "Deploying containers"
# Use 'up -d' to run containers in detached mode
docker-compose up -d
echo -e "${GREEN}Containers deployed successfully.${NC}"

# --- 4. Check Status ---
echo_step "Checking container status"
docker-compose ps

# --- 5. Completion ---
echo "----------------------------------------"
echo -e "${GREEN}RiskOptimizer deployed successfully via Docker Compose!${NC}"
echo -e "${BLUE}To stop the services, run: docker-compose down${NC}"
echo "----------------------------------------"
