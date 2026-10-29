#!/bin/bash

# =====================================================
# RiskOptimizer Test Runner Script
# =====================================================
# This script executes all unit and integration tests
# for the Python backend and Node.js frontends.
#
# PREREQUISITE: Run setup_environment.sh first.
# =====================================================

set -euo pipefail

PROJECT_ROOT=$(dirname "$0")
cd "$PROJECT_ROOT"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting all tests for RiskOptimizer...${NC}"
TEST_EXIT_CODE=0

# --- Helper Functions ---
run_tests() {
  local component_name="$1"
  local component_dir="$2"
  local test_command="$3"

  echo "----------------------------------------"
  echo -e "${BLUE}Running tests for $component_name in $component_dir...${NC}"

  if [ -d "$component_dir" ]; then
    (
      cd "$component_dir"
      echo "Executing: $test_command"
      if eval "$test_command"; then
        echo -e "${GREEN}$component_name tests passed.${NC}"
      else
        echo -e "${RED}$component_name tests FAILED. See output above.${NC}"
        TEST_EXIT_CODE=1
      fi
    )
  else
    echo -e "${RED}Warning: Directory $component_dir not found. Skipping $component_name tests.${NC}"
  fi
}

# --- 1. Python Backend Tests (using pytest) ---
# Assumes pytest is installed in the virtual environment
if [ -f "code/backend/venv/bin/activate" ]; then
  source "code/backend/venv/bin/activate"
  echo "Python virtual environment activated."
fi

run_tests "Python Backend" "code/backend" "pytest"

if command -v deactivate &> /dev/null; then
  deactivate
  echo "Python virtual environment deactivated."
fi

# --- 2. Web Frontend Tests (using npm test) ---
run_tests "Web Frontend" "web-frontend" "npm test"

# --- 3. Mobile Frontend Tests (using npm test) ---
run_tests "Mobile Frontend" "mobile-frontend" "npm test"

# --- 4. Blockchain Tests (using truffle test or hardhat test) ---
run_tests "Blockchain Contracts" "code/blockchain" "npm test"

echo "----------------------------------------"
if [ "$TEST_EXIT_CODE" -eq 0 ]; then
  echo -e "${GREEN}All RiskOptimizer tests completed successfully!${NC}"
else
  echo -e "${RED}Some tests failed. Please review the output.${NC}"
fi
echo "----------------------------------------"

exit "$TEST_EXIT_CODE"
