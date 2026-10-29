#!/bin/bash

# =====================================================
# RiskOptimizer Environment Setup Script
# =====================================================
# This script sets up the development environment for
# the RiskOptimizer project.
#
# It installs necessary system packages, sets up Python
# and Node.js environments, and installs dependencies
# for all project components.
#
# Tested on Ubuntu 22.04
# =====================================================

set -euo pipefail # Exit on error, unset variable, and pipe failure

# Get the directory where the script is located
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# --- Helper Functions ---
echo_step() {
    echo ""
    echo "====================================================="
    echo "STEP: $1"
    echo "====================================================="
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: Required command '$1' is not installed. Please install it."
        exit 1
    fi
}

# --- Prerequisites Installation ---
echo_step "Updating package list and installing prerequisites"
# Note: Using 'sudo' for system-wide package installation is necessary.
# The user must have sudo privileges.
sudo apt-get update
sudo apt-get install -y git python3 python3-pip python3-venv nodejs npm postgresql-client build-essential

# Verify installations
check_command git
check_command python3
check_command pip3
check_command node
check_command npm

echo "Prerequisites installed successfully."

# --- Environment Variable Setup ---
echo_step "Setting up Environment Variables"
ENV_FILE="$PROJECT_DIR/env.example" # Use env.example as a template
if [ -f "$ENV_FILE" ]; then
    echo "Please copy and rename '$ENV_FILE' to '.env' and fill in your credentials."
    echo "Required variables include POSTGRES_URI, ALPHA_VANTAGE_KEY, etc."
    echo "Example: cp $ENV_FILE .env"
else
    echo "Warning: env.example file not found. Please create a .env file based on the README."
fi

# --- Backend Setup (Python) ---
echo_step "Setting up Backend Environment (Python)"
BACKEND_DIR="$PROJECT_DIR/code/backend"
PYTHON_VENV_DIR="$PROJECT_DIR/venv" # Centralized venv for simplicity

if [ ! -d "$PYTHON_VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$PYTHON_VENV_DIR"
else
    echo "Python virtual environment already exists."
fi

echo "Activating virtual environment and installing backend dependencies..."
# Check if activation script exists before sourcing
if [ -f "$PYTHON_VENV_DIR/bin/activate" ]; then
    source "$PYTHON_VENV_DIR/bin/activate"
else
    echo "Error: Virtual environment activation script not found."
    exit 1
fi

if [ -f "$BACKEND_DIR/requirements.txt" ]; then
    pip install -r "$BACKEND_DIR/requirements.txt"
else
    echo "Warning: $BACKEND_DIR/requirements.txt not found. Skipping backend dependency install."
fi

deactivate
echo "Backend dependencies installed."

# --- Web Frontend Setup (Node.js/Vite/React) ---
echo_step "Setting up Web Frontend Environment (Node.js)"
WEB_FRONTEND_DIR="$PROJECT_DIR/web-frontend"

if [ -d "$WEB_FRONTEND_DIR" ]; then
    echo "Installing web frontend dependencies using npm..."
    cd "$WEB_FRONTEND_DIR"
    npm install --silent --no-progress
    cd "$PROJECT_DIR" # Return to project root
    echo "Web frontend dependencies installed."
else
    echo "Warning: Web frontend directory '$WEB_FRONTEND_DIR' not found. Skipping setup."
fi

# --- Mobile Frontend Setup (Node.js/React Native) ---
echo_step "Setting up Mobile Frontend Environment (Node.js/React Native)"
MOBILE_FRONTEND_DIR="$PROJECT_DIR/mobile-frontend"

if [ -d "$MOBILE_FRONTEND_DIR" ]; then
    echo "Installing mobile frontend dependencies using npm..."
    cd "$MOBILE_FRONTEND_DIR"
    npm install --silent --no-progress
    cd "$PROJECT_DIR" # Return to project root
    echo "Mobile frontend dependencies installed."
    echo "NOTE: React Native development requires additional setup (SDKs, etc.)."
    echo "Please refer to the official React Native documentation."
else
    echo "Warning: Mobile frontend directory '$MOBILE_FRONTEND_DIR' not found. Skipping setup."
fi

# --- Blockchain Setup (Truffle) ---
echo_step "Setting up Blockchain Environment (Truffle)"
BLOCKCHAIN_DIR="$PROJECT_DIR/code/blockchain"

if [ -d "$BLOCKCHAIN_DIR" ]; then
    echo "Installing Truffle locally in the blockchain directory..."
    cd "$BLOCKCHAIN_DIR"
    # Install Truffle and other dependencies defined in package.json
    if [ -f "package.json" ]; then
        npm install --silent --no-progress
    else
        echo "Warning: package.json not found in $BLOCKCHAIN_DIR. Skipping dependency install."
    fi
    cd "$PROJECT_DIR" # Return to project root
    echo "Blockchain dependencies installed."
else
    echo "Warning: Blockchain directory '$BLOCKCHAIN_DIR' not found. Skipping setup."
fi

# --- Custom Scripts Setup ---
echo_step "Making Custom Scripts Executable"
# Only make the scripts we found and updated executable
for script in lint-all.sh run_riskoptimizer.sh setup_environment.sh; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        echo "Made $script executable."
    fi
done

echo "----------------------------------------"
echo "RiskOptimizer Environment Setup Complete!"
echo "----------------------------------------"
