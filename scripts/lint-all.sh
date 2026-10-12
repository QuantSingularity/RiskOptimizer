#!/bin/bash

# =====================================================
# RiskOptimizer Linting and Fixing Script
# =====================================================
# This script runs linters and formatters for the project
# components (Python, JavaScript, HTML, CSS).
#
# PREREQUISITE: Run setup_environment.sh first to ensure
# all dependencies and tools are installed.
# =====================================================

set -euo pipefail # Exit on error, unset variable, and pipe failure

PROJECT_ROOT=$(dirname "$0")
cd "$PROJECT_ROOT"

echo "----------------------------------------"
echo "Starting linting and fixing process for RiskOptimizer..."
echo "----------------------------------------"

# --- Helper Functions ---

# Function to check if a command exists in the PATH
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to run a linter/formatter in a specific directory
run_linter() {
  local component_name="$1"
  local component_dir="$2"
  local linter_command="$3"
  local success_message="$4"

  echo "----------------------------------------"
  echo "Running $component_name linting in $component_dir..."

  if [ -d "$component_dir" ]; then
    (
      cd "$component_dir"
      echo "Executing: $linter_command"
      # Execute the command, capturing the exit code
      if eval "$linter_command"; then
        echo "$success_message"
      else
        echo "ERROR: $component_name linting failed. Please review the output above."
        exit 1
      fi
    )
  else
    echo "Warning: Directory $component_dir not found. Skipping $component_name linting."
  fi
}

# --- 1. Python Linting (Backend/AI Models) ---
# Assumes flake8 is installed in the virtual environment

# Activate the virtual environment for Python tools
if [ -f "code/backend/venv/bin/activate" ]; then
  source "code/backend/venv/bin/activate"
  echo "Python virtual environment activated."
else
  echo "Warning: Python virtual environment not found. Ensure setup_environment.sh has been run."
fi

# Run flake8 on Python code directories
run_linter "Python (flake8)" "code/backend" "flake8 ." "Python linting completed."
run_linter "Python (ruff)" "code/quant_ml" "ruff check ." "quant_ml linting completed."

# Deactivate the virtual environment
if command_exists deactivate; then
  deactivate
  echo "Python virtual environment deactivated."
fi

# --- 2. JavaScript/TypeScript Linting (Web/Mobile Frontend) ---
# Assumes ESLint and Prettier are installed locally via npm

# Run ESLint and Prettier for web-frontend
run_linter "Web Frontend (ESLint/Prettier)" "web-frontend" "npm run lint -- --fix && npm run format" "Web Frontend linting and formatting completed."

# Run ESLint and Prettier for mobile-frontend
run_linter "Mobile Frontend (ESLint/Prettier)" "mobile-frontend" "npm run lint -- --fix && npm run format" "Mobile Frontend linting and formatting completed."

# --- 3. Blockchain Linting (Truffle/Solidity) ---
# Assumes appropriate tools are installed locally

run_linter "Blockchain (Truffle/Solidity)" "code/blockchain" "npm run lint" "Blockchain linting completed."

echo "----------------------------------------"
echo "Linting and fixing process for RiskOptimizer completed successfully!"
echo "----------------------------------------"
