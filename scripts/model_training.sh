#!/bin/bash

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

set -euo pipefail

log() {
    local level=$1
    local message=$2
    local color=$NC
    case $level in
        "INFO") color=$BLUE ;;
        "SUCCESS") color=$GREEN ;;
        "WARNING") color=$YELLOW ;;
        "ERROR") color=$RED ;;
    esac
    echo -e "${color}[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message${NC}"
}

trap 'log "ERROR" "An error occurred on line $LINENO"' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
QUANT_ML_DIR="$PROJECT_ROOT/code/quant_ml"

MODEL_TYPE="all"
SYMBOLS=()
DATA_DIR=""
MODEL_PATH=""
RISK_TOLERANCE="5"
OUTPUT_DIR=""
EVALUATE_ONLY=false
SAVE_METRICS=true
STRICT=false
VISUALIZE=false

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Train and evaluate the quant_ml models for RiskOptimizer"
    echo ""
    echo "Options:"
    echo "  -m, --model TYPE           all, optimization, risk or forecast (default: all)"
    echo "                             optimization trains and saves the portfolio optimizer;"
    echo "                             risk and forecast are fitted on demand and are only evaluated"
    echo "  -s, --symbols SYMBOLS      Space separated symbols to use (default: every bundled dataset)"
    echo "  -d, --data-dir DIR         Directory containing <SYMBOL>_historical.csv files"
    echo "  -r, --risk-tolerance N     Risk tolerance from 1 to 10 for training (default: 5)"
    echo "  -o, --model-path FILE      Where to save the trained optimizer (default: quant_ml artifacts)"
    echo "      --output-dir DIR       Where to write evaluation.json (default: quant_ml artifacts)"
    echo "      --evaluate-only        Skip training and only evaluate"
    echo "      --no-metrics           Skip the evaluation step"
    echo "      --strict               Exit with an error if any calibration check fails"
    echo "      --visualize            Save efficient frontier and Monte Carlo plots after training"
    echo "  -h, --help                 Show this help message"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model) MODEL_TYPE="$2"; shift 2 ;;
        -s|--symbols)
            shift
            while [[ $# -gt 0 && "$1" != -* ]]; do SYMBOLS+=("$1"); shift; done
            ;;
        -d|--data-dir) DATA_DIR="$2"; shift 2 ;;
        -r|--risk-tolerance) RISK_TOLERANCE="$2"; shift 2 ;;
        -o|--model-path) MODEL_PATH="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        --evaluate-only) EVALUATE_ONLY=true; shift ;;
        --no-metrics) SAVE_METRICS=false; shift ;;
        --strict) STRICT=true; shift ;;
        --visualize) VISUALIZE=true; shift ;;
        -h|--help) print_usage; exit 0 ;;
        *) log "ERROR" "Unknown option: $1"; print_usage; exit 1 ;;
    esac
done

if [[ ! "$MODEL_TYPE" =~ ^(all|optimization|risk|forecast)$ ]]; then
    log "ERROR" "Invalid model type: $MODEL_TYPE"
    print_usage
    exit 1
fi

if [ ! -d "$QUANT_ML_DIR" ]; then
    log "ERROR" "quant_ml directory not found at $QUANT_ML_DIR"
    exit 1
fi

activate_venv() {
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        log "INFO" "Activated virtual environment"
    else
        log "WARNING" "Virtual environment not found at $PROJECT_ROOT/venv; creating it"
        python3 -m venv "$PROJECT_ROOT/venv"
        source "$PROJECT_ROOT/venv/bin/activate"
        log "SUCCESS" "Created and activated virtual environment"
    fi
}

install_quant_ml() {
    log "INFO" "Installing quant_ml and its dependencies..."
    pip install --quiet -e "$QUANT_ML_DIR"
    log "SUCCESS" "quant_ml installed"
}

common_data_arguments() {
    DATA_ARGUMENTS=()
    if [ ${#SYMBOLS[@]} -gt 0 ]; then
        DATA_ARGUMENTS+=(--symbols "${SYMBOLS[@]}")
    fi
    if [ -n "$DATA_DIR" ]; then
        DATA_ARGUMENTS+=(--data-dir "$DATA_DIR")
    fi
}

train_optimization_model() {
    log "INFO" "Training the portfolio optimizer..."
    common_data_arguments
    local arguments=("${DATA_ARGUMENTS[@]}" --risk-tolerance "$RISK_TOLERANCE")
    if [ -n "$MODEL_PATH" ]; then
        arguments+=(--model-path "$MODEL_PATH")
    fi
    if [ "$VISUALIZE" = true ]; then
        arguments+=(--visualize)
    fi
    python -m quant_ml.training.cli "${arguments[@]}"
    log "SUCCESS" "Portfolio optimizer trained"
}

evaluate_models() {
    log "INFO" "Evaluating models..."
    common_data_arguments
    local target_dir="${OUTPUT_DIR:-${QUANT_ML_ARTIFACT_DIR:-$QUANT_ML_DIR/artifacts}/evaluation}"
    mkdir -p "$target_dir"
    local arguments=("${DATA_ARGUMENTS[@]}" --output "$target_dir/evaluation.json")
    if [ "$STRICT" = true ]; then
        arguments+=(--strict)
    fi
    python -m quant_ml.training.evaluate "${arguments[@]}"
    log "SUCCESS" "Evaluation report written to $target_dir/evaluation.json"
}

log "INFO" "Starting quant_ml model training and evaluation..."
activate_venv
install_quant_ml

if [ "$EVALUATE_ONLY" = false ]; then
    if [ "$MODEL_TYPE" = "all" ] || [ "$MODEL_TYPE" = "optimization" ]; then
        train_optimization_model
    else
        log "INFO" "$MODEL_TYPE models are fitted on demand; nothing to train"
    fi
fi

if [ "$SAVE_METRICS" = true ]; then
    evaluate_models
fi

deactivate
log "SUCCESS" "quant_ml model training and evaluation completed"
