#!/bin/bash

# =====================================================
# RiskOptimizer Application Run Script
# =====================================================
# This script starts the backend and web-frontend components
# of the RiskOptimizer application.
#
# PREREQUISITE: Run setup_environment.sh first to ensure
# all dependencies and tools are installed.
# =====================================================

set -euo pipefail # Exit on error, unset variable, and pipe failure

PROJECT_ROOT=$(dirname "$0")
cd "$PROJECT_ROOT"

# --- Configuration ---
BACKEND_DIR="code/backend"
FRONTEND_DIR="web-frontend"
VENV_DIR="$BACKEND_DIR/venv"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting RiskOptimizer application...${NC}"

# --- Helper Functions ---

# Function to check if a directory exists
check_dir() {
  if [ ! -d "$1" ]; then
    echo -e "${RED}Error: Required directory '$1' not found. Please ensure the repository is complete and correctly structured.${NC}"
    exit 1
  fi
}

# Function for graceful shutdown
cleanup() {
  echo -e "\n${BLUE}Stopping services...${NC}"
  # Check if PIDs are set and processes are running before killing
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "Stopping Frontend (PID: ${FRONTEND_PID})..."
    kill "$FRONTEND_PID"
  fi
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "Stopping Backend (PID: ${BACKEND_PID})..."
    kill "$BACKEND_PID"
  fi
  echo -e "${GREEN}All services stopped.${NC}"
  exit 0
}

# Trap SIGINT (Ctrl+C) to call the cleanup function
trap cleanup SIGINT

# --- 1. Start Backend Server ---
check_dir "$BACKEND_DIR"

echo -e "${BLUE}Starting backend server...${NC}"
(
  cd "$BACKEND_DIR"
  # Check for and activate virtual environment
  if [ -f "../$VENV_DIR/bin/activate" ]; then
    source "../$VENV_DIR/bin/activate"
  elif [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
  else
    echo -e "${RED}Error: Python virtual environment not found at $VENV_DIR. Please run setup_environment.sh first.${NC}"
    exit 1
  fi

  # Run the backend application in the background
  # Using 'exec' to replace the current shell with the python process,
  # but since we need to run it in the background, we use 'python app.py &'
  # Consider using a proper WSGI server like gunicorn in a production environment.
  echo "Running: python app.py"
  python app.py &
  BACKEND_PID=$!
  echo -e "${GREEN}Backend started with PID: ${BACKEND_PID}${NC}"
) & # Run the entire block in a subshell to manage directory changes and venv activation
BACKEND_PID=$!

# --- 2. Wait for Backend to Initialize ---
# NOTE: Using 'sleep' is a simple but unreliable way to wait.
# For a robust solution, implement a health check endpoint and poll it here.
echo -e "${BLUE}Waiting for backend to initialize (5 seconds)...${NC}"
sleep 5

# --- 3. Start Web Frontend ---
check_dir "$FRONTEND_DIR"

echo -e "${BLUE}Starting web frontend...${NC}"
(
  cd "$FRONTEND_DIR"
  # Check if dependencies are installed
  if [ ! -d "node_modules" ]; then
    echo "Warning: node_modules not found. Running 'npm install'..."
    npm install --silent --no-progress
  fi

  # Run the frontend application in the background
  echo "Running: npm start"
  npm start &
  FRONTEND_PID=$!
  echo -e "${GREEN}Frontend started with PID: ${FRONTEND_PID}${NC}"
) &
FRONTEND_PID=$!

# --- 4. Final Status and Wait ---
echo -e "\n${GREEN}RiskOptimizer application is running!${NC}"
echo -e "${GREEN}Backend PID: ${BACKEND_PID}${NC}"
echo -e "${GREEN}Frontend PID: ${FRONTEND_PID}${NC}"
echo -e "${GREEN}Access the application at: http://localhost:3000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"

# Wait for the trap to be triggered (e.g., by Ctrl+C)
wait
