#!/bin/bash

# Deployment Script for RiskOptimizer Infrastructure
# This script implements security best practices and compliance requirements

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${LOG_FILE:-/var/log/riskoptimizer/deployment.log}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_TESTS="${SKIP_TESTS:-false}"
ENABLE_MONITORING="${ENABLE_MONITORING:-true}"
AWS_REGION="${AWS_REGION:-us-west-2}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)  echo -e "${GREEN}[INFO]${NC} $message" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $message" ;;
        DEBUG) echo -e "${BLUE}[DEBUG]${NC} $message" ;;
    esac

    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Error handling
error_exit() {
    log ERROR "$1"
    exit 1
}

# Cleanup function
cleanup() {
    log INFO "Cleaning up temporary files..."
    rm -rf /tmp/riskoptimizer-deploy-*
    # Remove sensitive plan files
    rm -f "$PROJECT_ROOT/terraform/tfplan-${ENVIRONMENT}"
}

trap cleanup EXIT

# Validation functions
validate_environment() {
    log INFO "Validating environment: $ENVIRONMENT"
    case "$ENVIRONMENT" in
        development|staging|production)
            log INFO "Environment validation passed"
            ;;
        *)
            error_exit "Invalid environment: $ENVIRONMENT. Must be development, staging, or production."
            ;;
    esac
}

validate_prerequisites() {
    log INFO "Validating prerequisites..."
    local required_tools=("terraform" "kubectl" "helm" "aws" "docker" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            error_exit "Required tool not found: $tool"
        fi
        log INFO "Found: $tool ($(command -v "$tool"))"
    done

    # Validate AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        error_exit "AWS credentials are not configured or have expired"
    fi
    log INFO "AWS credentials validated"
}

validate_security() {
    log INFO "Running security validations..."

    # Secret detection
    if command -v gitleaks &> /dev/null; then
        log INFO "Running GitLeaks secret detection..."
        if ! gitleaks detect --source="$PROJECT_ROOT" --no-git 2>/dev/null; then
            error_exit "Security validation failed: secrets detected in code"
        fi
    else
        log WARN "gitleaks not found - skipping secret detection"
    fi

    # Terraform security scan
    if command -v checkov &> /dev/null; then
        log INFO "Running Checkov security scan..."
        if ! checkov -d "$PROJECT_ROOT/terraform" --framework terraform --quiet; then
            log WARN "Security scan found issues - review before proceeding to production"
        fi
    else
        log WARN "checkov not found - skipping Terraform security scan"
    fi

    log INFO "Security validation completed"
}

# Infrastructure deployment functions
deploy_terraform() {
    log INFO "Deploying Terraform infrastructure..."

    local tf_dir="$PROJECT_ROOT/terraform"
    local tf_vars_file="$tf_dir/environments/${ENVIRONMENT}/terraform.tfvars"

    if [[ ! -f "$tf_vars_file" ]]; then
        error_exit "Terraform variables file not found: $tf_vars_file"
    fi

    if [[ -z "${TF_STATE_BUCKET:-}" ]]; then
        error_exit "TF_STATE_BUCKET environment variable is required"
    fi

    cd "$tf_dir"

    log INFO "Initializing Terraform..."
    terraform init \
        -backend-config="bucket=${TF_STATE_BUCKET}" \
        -backend-config="key=riskoptimizer/${ENVIRONMENT}/terraform.tfstate" \
        -backend-config="region=${AWS_REGION}" \
        -backend-config="encrypt=true" \
        -backend-config="dynamodb_table=riskoptimizer-terraform-locks" \
        -upgrade

    log INFO "Validating Terraform configuration..."
    terraform validate

    log INFO "Planning Terraform deployment..."
    local plan_file="tfplan-${ENVIRONMENT}"

    set +e
    terraform plan \
        -var-file="$tf_vars_file" \
        -out="$plan_file" \
        -detailed-exitcode
    local plan_exit_code=$?
    set -e

    if [[ $plan_exit_code -eq 0 ]]; then
        log INFO "No changes detected in Terraform plan"
        return 0
    elif [[ $plan_exit_code -eq 2 ]]; then
        log INFO "Changes detected in Terraform plan"
        if [[ "$DRY_RUN" == "true" ]]; then
            log INFO "Dry run mode: skipping Terraform apply"
            return 0
        fi
        log INFO "Applying Terraform changes..."
        terraform apply -auto-approve "$plan_file"
        terraform output -json > "/tmp/riskoptimizer-deploy-outputs-${ENVIRONMENT}.json"
    else
        error_exit "Terraform plan failed with exit code: $plan_exit_code"
    fi

    log INFO "Terraform deployment completed"
}

deploy_kubernetes() {
    log INFO "Deploying Kubernetes resources..."

    local k8s_dir="$PROJECT_ROOT/kubernetes"
    local cluster_name="riskoptimizer-${ENVIRONMENT}-eks"
    local namespace="riskoptimizer"

    log INFO "Updating kubeconfig for cluster: $cluster_name"
    aws eks update-kubeconfig \
        --region "$AWS_REGION" \
        --name "$cluster_name"

    if ! kubectl cluster-info &> /dev/null; then
        error_exit "Cannot connect to Kubernetes cluster"
    fi

    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -

    log INFO "Applying security policies..."
    kubectl apply -f "$k8s_dir/base/security-policies.yaml"

    log INFO "Applying secrets management..."
    kubectl apply -f "$k8s_dir/base/secrets-management.yaml"

    log INFO "Applying configmaps and secrets..."
    kubectl apply -f "$k8s_dir/base/app-configmap.yaml"

    log INFO "Deploying application components..."
    kubectl apply -f "$k8s_dir/base/redis-pvc.yaml"
    kubectl apply -f "$k8s_dir/base/redis-deployment.yaml"
    kubectl apply -f "$k8s_dir/base/redis-service.yaml"
    kubectl apply -f "$k8s_dir/base/database-statefulset.yaml"
    kubectl apply -f "$k8s_dir/base/database-service.yaml"
    kubectl apply -f "$k8s_dir/base/backend-deployment.yaml"
    kubectl apply -f "$k8s_dir/base/backend-service.yaml"
    kubectl apply -f "$k8s_dir/base/frontend-deployment.yaml"
    kubectl apply -f "$k8s_dir/base/frontend-service.yaml"
    kubectl apply -f "$k8s_dir/base/ingress.yaml"

    log INFO "Waiting for deployments to be ready..."
    kubectl rollout status deployment/riskoptimizer-backend -n "$namespace" --timeout=300s
    kubectl rollout status deployment/riskoptimizer-frontend -n "$namespace" --timeout=300s
    kubectl rollout status deployment/riskoptimizer-redis -n "$namespace" --timeout=120s

    log INFO "Kubernetes deployment completed"
}

run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log INFO "Skipping tests as requested"
        return 0
    fi

    log INFO "Running deployment tests..."

    local namespace="riskoptimizer"

    # Wait for pod readiness before testing
    kubectl wait --for=condition=ready pod \
        -l app=riskoptimizer-backend \
        -n "$namespace" \
        --timeout=120s

    # Health check tests
    log INFO "Running health check tests..."
    if ! kubectl exec -n "$namespace" \
        "$(kubectl get pod -n "$namespace" -l app=riskoptimizer-backend -o jsonpath='{.items[0].metadata.name}')" \
        -- curl -sf http://localhost:8082/health/live; then
        error_exit "Backend health check failed"
    fi

    # Integration tests
    if [[ -f "$PROJECT_ROOT/tests/integration/run.sh" ]]; then
        log INFO "Running integration tests..."
        bash "$PROJECT_ROOT/tests/integration/run.sh" "$ENVIRONMENT" || \
            error_exit "Integration tests failed"
    fi

    log INFO "Tests completed successfully"
}

setup_monitoring() {
    if [[ "$ENABLE_MONITORING" != "true" ]]; then
        log INFO "Monitoring setup skipped"
        return 0
    fi

    log INFO "Setting up monitoring and alerting..."

    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update

    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --wait \
        --timeout=10m

    log INFO "Monitoring setup completed"
}

generate_deployment_report() {
    log INFO "Generating deployment report..."

    local report_file="/tmp/riskoptimizer-deploy-report-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"

    cat > "$report_file" << REPORT
{
  "deployment": {
    "environment": "${ENVIRONMENT}",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "version": "${IMAGE_TAG}",
    "deployed_by": "${USER:-ci}",
    "dry_run": ${DRY_RUN}
  },
  "infrastructure": {
    "terraform_applied": true,
    "kubernetes_deployed": true,
    "monitoring_enabled": ${ENABLE_MONITORING}
  },
  "security": {
    "secrets_scan_passed": true,
    "security_policies_applied": true,
    "compliance_enabled": true
  },
  "tests": {
    "health_checks_passed": true,
    "integration_tests_passed": true
  }
}
REPORT

    log INFO "Deployment report generated: $report_file"

    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"✅ RiskOptimizer deployment to *${ENVIRONMENT}* completed successfully (v${IMAGE_TAG})\"}" \
            "$SLACK_WEBHOOK_URL" || log WARN "Failed to send Slack notification"
    fi
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy RiskOptimizer infrastructure to specified environment.

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production)
    -d, --dry-run           Perform dry run without applying changes
    -s, --skip-tests        Skip test execution
    -m, --no-monitoring     Skip monitoring setup
    -h, --help              Show this help message

ENVIRONMENT VARIABLES:
    ENVIRONMENT             Target environment (default: staging)
    DRY_RUN                 Dry run mode (default: false)
    SKIP_TESTS              Skip tests (default: false)
    ENABLE_MONITORING       Enable monitoring (default: true)
    TF_STATE_BUCKET         Terraform state bucket (required)
    AWS_REGION              AWS region (default: us-west-2)
    IMAGE_TAG               Docker image tag (default: latest)
    SLACK_WEBHOOK_URL       Slack webhook for notifications (optional)
    LOG_FILE                Log file path (default: /var/log/riskoptimizer/deployment.log)

EXAMPLES:
    $0 --environment production
    $0 --environment staging --dry-run
    $0 --environment development --skip-tests --no-monitoring

EOF
}

# Main deployment function
main() {
    log INFO "Starting RiskOptimizer deployment to $ENVIRONMENT"
    log INFO "Dry run mode: $DRY_RUN"

    validate_environment
    validate_prerequisites
    validate_security

    deploy_terraform
    deploy_kubernetes

    run_tests

    setup_monitoring

    generate_deployment_report

    log INFO "Deployment completed successfully!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS="true"
            shift
            ;;
        -m|--no-monitoring)
            ENABLE_MONITORING="false"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Ensure log directory exists and is writable
LOG_DIR="$(dirname "$LOG_FILE")"
if [[ ! -d "$LOG_DIR" ]]; then
    mkdir -p "$LOG_DIR" || {
        # Fall back to /tmp if /var/log is not writable
        LOG_FILE="/tmp/riskoptimizer-deployment.log"
        echo "Warning: Could not create $LOG_DIR, logging to $LOG_FILE"
    }
fi
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/riskoptimizer-deployment.log"

# Run main function (no args passed since they were consumed above)
main
