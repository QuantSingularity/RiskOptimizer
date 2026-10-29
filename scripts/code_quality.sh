#!/bin/bash
# code_quality.sh
# Comprehensive code quality automation script for RiskOptimizer
# This script handles linting, formatting, and code quality checks across all components

# Color definitions for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log function for consistent output
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

# Error handling function
handle_error() {
    log "ERROR" "An error occurred on line $1"
    exit 1
}

# Set up error handling
trap 'handle_error $LINENO' ERR

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Parse command line arguments
COMPONENT="all"
FIX=false
STAGED_ONLY=false
VERBOSE=false

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Run code quality checks for RiskOptimizer components"
    echo ""
    echo "Options:"
    echo "  -c, --component COMPONENT  Run checks for specific component"
    echo "                             (all, backend, frontend, quant_ml, blockchain)"
    echo "  -f, --fix                  Automatically fix issues when possible"
    echo "  -s, --staged               Only check staged files in git"
    echo "  -v, --verbose              Show verbose output"
    echo "  -h, --help                 Show this help message"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--component)
            COMPONENT="$2"
            shift 2
            ;;
        -f|--fix)
            FIX=true
            shift
            ;;
        -s|--staged)
            STAGED_ONLY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Validate component argument
if [[ ! "$COMPONENT" =~ ^(all|backend|frontend|quant_ml|blockchain)$ ]]; then
    log "ERROR" "Invalid component: $COMPONENT"
    print_usage
    exit 1
fi

# Function to activate virtual environment
activate_venv() {
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        log "INFO" "Activated virtual environment"
    else
        log "WARNING" "Virtual environment not found at $PROJECT_ROOT/venv"
        log "INFO" "Creating virtual environment..."
        python3 -m venv "$PROJECT_ROOT/venv"
        source "$PROJECT_ROOT/venv/bin/activate"
        log "SUCCESS" "Created and activated virtual environment"
    fi
}

# Function to get staged files for a specific component and extension
get_staged_files() {
    local component=$1
    local extension=$2

    if [ "$STAGED_ONLY" = true ]; then
        git diff --cached --name-only --diff-filter=ACMR | grep -E "^code/$component/.*\.$extension$" || true
    else
        find "$PROJECT_ROOT/code/$component" -name "*.$extension" -type f | sort
    fi
}

# Function to run Python linting and formatting
run_ruff_linting() {
    local component=$1
    log "INFO" "Running ruff for $component..."

    pip install ruff > /dev/null

    local component_dir="$PROJECT_ROOT/code/$component"
    local report_dir="$PROJECT_ROOT/code_quality_reports/$component"
    mkdir -p "$report_dir"

    local status=0
    if [ "$FIX" = true ]; then
        (cd "$component_dir" && ruff check . --fix > "$report_dir/ruff.txt" 2>&1) || status=1
        (cd "$component_dir" && ruff format . > "$report_dir/ruff_format.txt" 2>&1) || status=1
        log "SUCCESS" "Applied ruff fixes and formatting"
    else
        (cd "$component_dir" && ruff check . > "$report_dir/ruff.txt" 2>&1) || status=1
        (cd "$component_dir" && ruff format --check . > "$report_dir/ruff_format.txt" 2>&1) || status=1
    fi

    if [ "$VERBOSE" = true ]; then
        cat "$report_dir/ruff.txt" "$report_dir/ruff_format.txt"
    fi

    if [ "$status" -ne 0 ]; then
        log "WARNING" "ruff reported issues for $component; see $report_dir"
    else
        log "SUCCESS" "ruff checks passed for $component"
    fi
}

run_python_linting() {
    local component=$1
    log "INFO" "Running Python linting for $component..."

    # Install linting tools if needed
    pip install flake8 black isort mypy > /dev/null

    # Get Python files to check
    local python_files=()
    if [ "$STAGED_ONLY" = true ]; then
        mapfile -t python_files < <(get_staged_files "$component" "py")
    else
        mapfile -t python_files < <(find "$PROJECT_ROOT/code/$component" -name "*.py" -type f | sort)
    fi

    if [ ${#python_files[@]} -eq 0 ]; then
        log "INFO" "No Python files to check for $component"
        return 0
    fi

    # Create reports directory
    mkdir -p "$PROJECT_ROOT/code_quality_reports/$component"

    # Run flake8
    log "INFO" "Running flake8..."
    if [ "$VERBOSE" = true ]; then
        flake8 "${python_files[@]}" --statistics
    else
        flake8 "${python_files[@]}" --statistics > "$PROJECT_ROOT/code_quality_reports/$component/flake8.txt"
    fi

    # Run black
    log "INFO" "Running black..."
    if [ "$FIX" = true ]; then
        if [ "$VERBOSE" = true ]; then
            black "${python_files[@]}"
        else
            black "${python_files[@]}" > /dev/null
        fi
        log "SUCCESS" "Formatted Python files with black"
    else
        if [ "$VERBOSE" = true ]; then
            black --check "${python_files[@]}"
        else
            black --check "${python_files[@]}" > "$PROJECT_ROOT/code_quality_reports/$component/black.txt" 2>&1 || true
        fi
    fi

    # Run isort
    log "INFO" "Running isort..."
    if [ "$FIX" = true ]; then
        if [ "$VERBOSE" = true ]; then
            isort "${python_files[@]}"
        else
            isort "${python_files[@]}" > /dev/null
        fi
        log "SUCCESS" "Sorted imports with isort"
    else
        if [ "$VERBOSE" = true ]; then
            isort --check-only "${python_files[@]}"
        else
            isort --check-only "${python_files[@]}" > "$PROJECT_ROOT/code_quality_reports/$component/isort.txt" 2>&1 || true
        fi
    fi

    # Run mypy for type checking
    log "INFO" "Running mypy..."
    if [ "$VERBOSE" = true ]; then
        mypy "${python_files[@]}" || true
    else
        mypy "${python_files[@]}" > "$PROJECT_ROOT/code_quality_reports/$component/mypy.txt" 2>&1 || true
    fi

    log "SUCCESS" "Python linting completed for $component"
}

# Function to run JavaScript/TypeScript linting and formatting
run_js_linting() {
    local component=$1
    log "INFO" "Running JavaScript/TypeScript linting for $component..."

    cd "$PROJECT_ROOT/code/$component" || { log "ERROR" "Directory not found: $PROJECT_ROOT/code/$component"; return 1; }

    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        log "WARNING" "No package.json found in $component, skipping JavaScript/TypeScript linting"
        return 0
    fi

    # Install ESLint and Prettier if needed
    if ! npm list -g eslint > /dev/null 2>&1; then
        log "INFO" "Installing ESLint and Prettier..."
        npm install -g eslint prettier > /dev/null
    fi

    # Get JS/TS files to check
    local js_files=()
    if [ "$STAGED_ONLY" = true ]; then
        mapfile -t js_files < <(get_staged_files "$component" "js|jsx|ts|tsx")
    else
        mapfile -t js_files < <(find . -regex ".*\.\(js\|jsx\|ts\|tsx\)" -type f | sort)
    fi

    if [ ${#js_files[@]} -eq 0 ]; then
        log "INFO" "No JavaScript/TypeScript files to check for $component"
        return 0
    fi

    # Create reports directory
    mkdir -p "$PROJECT_ROOT/code_quality_reports/$component"

    # Run ESLint
    log "INFO" "Running ESLint..."
    if [ "$FIX" = true ]; then
        if [ "$VERBOSE" = true ]; then
            npx eslint --fix "${js_files[@]}" || true
        else
            npx eslint --fix "${js_files[@]}" > /dev/null 2>&1 || true
        fi
        log "SUCCESS" "Fixed JavaScript/TypeScript files with ESLint"
    else
        if [ "$VERBOSE" = true ]; then
            npx eslint "${js_files[@]}" || true
        else
            npx eslint "${js_files[@]}" > "$PROJECT_ROOT/code_quality_reports/$component/eslint.txt" 2>&1 || true
        fi
    fi

    # Run Prettier
    log "INFO" "Running Prettier..."
    if [ "$FIX" = true ]; then
        if [ "$VERBOSE" = true ]; then
            npx prettier --write "${js_files[@]}" || true
        else
            npx prettier --write "${js_files[@]}" > /dev/null 2>&1 || true
        fi
        log "SUCCESS" "Formatted JavaScript/TypeScript files with Prettier"
    else
        if [ "$VERBOSE" = true ]; then
            npx prettier --check "${js_files[@]}" || true
        else
            npx prettier --check "${js_files[@]}" > "$PROJECT_ROOT/code_quality_reports/$component/prettier.txt" 2>&1 || true
        fi
    fi

    log "SUCCESS" "JavaScript/TypeScript linting completed for $component"
}

# Function to run Solidity linting
run_solidity_linting() {
    local component=$1
    log "INFO" "Running Solidity linting for $component..."

    cd "$PROJECT_ROOT/code/$component" || { log "ERROR" "Directory not found: $PROJECT_ROOT/code/$component"; return 1; }

    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        log "WARNING" "No package.json found in $component, skipping Solidity linting"
        return 0
    fi

    # Get Solidity files to check
    local sol_files=()
    if [ "$STAGED_ONLY" = true ]; then
        mapfile -t sol_files < <(get_staged_files "$component" "sol")
    else
        mapfile -t sol_files < <(find . -name "*.sol" -type f | sort)
    fi

    if [ ${#sol_files[@]} -eq 0 ]; then
        log "INFO" "No Solidity files to check for $component"
        return 0
    fi

    # Create reports directory
    mkdir -p "$PROJECT_ROOT/code_quality_reports/$component"

    # Run Solhint
    log "INFO" "Running Solhint..."
    if ! npm list -g solhint > /dev/null 2>&1; then
        log "INFO" "Installing Solhint..."
        npm install -g solhint > /dev/null
    fi

    if [ "$FIX" = true ]; then
        if [ "$VERBOSE" = true ]; then
            npx solhint --fix "${sol_files[@]}" || true
        else
            npx solhint --fix "${sol_files[@]}" > /dev/null 2>&1 || true
        fi
        log "SUCCESS" "Fixed Solidity files with Solhint"
    else
        if [ "$VERBOSE" = true ]; then
            npx solhint "${sol_files[@]}" || true
        else
            npx solhint "${sol_files[@]}" > "$PROJECT_ROOT/code_quality_reports/$component/solhint.txt" 2>&1 || true
        fi
    fi

    log "SUCCESS" "Solidity linting completed for $component"
}

# Function to generate code quality report
generate_quality_report() {
    log "INFO" "Generating code quality report..."

    # Create report directory
    REPORT_DIR="$PROJECT_ROOT/code_quality_reports"
    mkdir -p "$REPORT_DIR"

    # Generate HTML report
    cat > "$REPORT_DIR/index.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>RiskOptimizer Code Quality Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #333; }
        .summary { background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .component { margin-bottom: 30px; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
</head>
<body>
    <h1>RiskOptimizer Code Quality Report</h1>
    <div class="summary">
        <h2>Quality Check Summary</h2>
        <p>Generated on: $(date)</p>
        <p>Components checked: $COMPONENT</p>
        <p>Auto-fix mode: $FIX</p>
        <p>Staged files only: $STAGED_ONLY</p>
    </div>
EOF

    # Add component sections
    if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "backend" ]; then
        if [ -d "$REPORT_DIR/backend" ]; then
            cat >> "$REPORT_DIR/index.html" << EOF
    <div class="component">
        <h2>Backend</h2>
        <h3>Python Quality Checks</h3>
        <ul>
EOF
            if [ -f "$REPORT_DIR/backend/flake8.txt" ]; then
                echo '<li><a href="backend/flake8.txt">Flake8 Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            if [ -f "$REPORT_DIR/backend/black.txt" ]; then
                echo '<li><a href="backend/black.txt">Black Formatting Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            if [ -f "$REPORT_DIR/backend/isort.txt" ]; then
                echo '<li><a href="backend/isort.txt">Import Sorting Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            if [ -f "$REPORT_DIR/backend/mypy.txt" ]; then
                echo '<li><a href="backend/mypy.txt">Type Checking Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            cat >> "$REPORT_DIR/index.html" << EOF
        </ul>
    </div>
EOF
        fi
    fi

    if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "frontend" ]; then
        if [ -d "$REPORT_DIR/web-frontend" ]; then
            cat >> "$REPORT_DIR/index.html" << EOF
    <div class="component">
        <h2>Web Frontend</h2>
        <h3>JavaScript/TypeScript Quality Checks</h3>
        <ul>
EOF
            if [ -f "$REPORT_DIR/web-frontend/eslint.txt" ]; then
                echo '<li><a href="web-frontend/eslint.txt">ESLint Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            if [ -f "$REPORT_DIR/web-frontend/prettier.txt" ]; then
                echo '<li><a href="web-frontend/prettier.txt">Prettier Formatting Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            cat >> "$REPORT_DIR/index.html" << EOF
        </ul>
    </div>
EOF
        fi
    fi

    if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "quant_ml" ]; then
        if [ -d "$REPORT_DIR/quant_ml" ]; then
            cat >> "$REPORT_DIR/index.html" << EOF
    <div class="component">
        <h2>quant_ml</h2>
        <h3>Python Quality Checks</h3>
        <ul>
EOF
            if [ -f "$REPORT_DIR/quant_ml/ruff.txt" ]; then
                echo '<li><a href="quant_ml/ruff.txt">Ruff Lint Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            if [ -f "$REPORT_DIR/quant_ml/ruff_format.txt" ]; then
                echo '<li><a href="quant_ml/ruff_format.txt">Ruff Formatting Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            cat >> "$REPORT_DIR/index.html" << EOF
        </ul>
    </div>
EOF
        fi
    fi

    if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "blockchain" ]; then
        if [ -d "$REPORT_DIR/blockchain" ]; then
            cat >> "$REPORT_DIR/index.html" << EOF
    <div class="component">
        <h2>Blockchain</h2>
        <h3>JavaScript/TypeScript Quality Checks</h3>
        <ul>
EOF
            if [ -f "$REPORT_DIR/blockchain/eslint.txt" ]; then
                echo '<li><a href="blockchain/eslint.txt">ESLint Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            if [ -f "$REPORT_DIR/blockchain/prettier.txt" ]; then
                echo '<li><a href="blockchain/prettier.txt">Prettier Formatting Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            cat >> "$REPORT_DIR/index.html" << EOF
        </ul>
        <h3>Solidity Quality Checks</h3>
        <ul>
EOF
            if [ -f "$REPORT_DIR/blockchain/solhint.txt" ]; then
                echo '<li><a href="blockchain/solhint.txt">Solhint Report</a></li>' >> "$REPORT_DIR/index.html"
            fi
            cat >> "$REPORT_DIR/index.html" << EOF
        </ul>
    </div>
EOF
        fi
    fi

    # Complete the HTML
    cat >> "$REPORT_DIR/index.html" << EOF
</body>
</html>
EOF

    log "SUCCESS" "Code quality report generated at $REPORT_DIR/index.html"
}

# Main execution
log "INFO" "Starting RiskOptimizer code quality checks..."

# Activate virtual environment for Python checks
activate_venv

# Run checks based on component selection
if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "backend" ]; then
    run_python_linting "backend"
fi

if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "quant_ml" ]; then
    run_ruff_linting "quant_ml"
fi

if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "frontend" ]; then
    run_js_linting "web-frontend"
fi

if [ "$COMPONENT" = "all" ] || [ "$COMPONENT" = "blockchain" ]; then
    run_js_linting "blockchain"
    run_solidity_linting "blockchain"
fi

# Generate combined quality report
generate_quality_report

# Deactivate virtual environment
deactivate

log "SUCCESS" "All code quality checks completed!"
exit 0
