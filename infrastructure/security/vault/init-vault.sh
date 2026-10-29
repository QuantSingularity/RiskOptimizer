#!/bin/bash

# Vault Initialization and Configuration Script
# This script initializes Vault and sets up the basic configuration for RiskOptimizer

set -euo pipefail

# Configuration variables
VAULT_ADDR="${VAULT_ADDR:-https://vault.riskoptimizer.com:8200}"
VAULT_NAMESPACE="${VAULT_NAMESPACE:-}"
VAULT_INIT_FILE="/opt/vault/data/vault-init.json"
VAULT_POLICIES_DIR="/opt/vault/policies"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if Vault is already initialized
check_vault_status() {
    log "Checking Vault status..."

    if vault status >/dev/null 2>&1; then
        log "Vault is accessible"

        if vault status | grep -q "Initialized.*true"; then
            log "Vault is already initialized"
            return 0
        else
            log "Vault is not initialized"
            return 1
        fi
    else
        error "Cannot connect to Vault at $VAULT_ADDR"
    fi
}

# Initialize Vault
initialize_vault() {
    log "Initializing Vault..."

    # Initialize with 5 key shares and threshold of 3
    vault operator init \
        -key-shares=5 \
        -key-threshold=3 \
        -format=json > "$VAULT_INIT_FILE"

    log "Vault initialized successfully"
    chmod 600 "$VAULT_INIT_FILE"
    warn "IMPORTANT: Store the unseal keys and root token securely!"
    warn "Unseal keys and root token saved to: $VAULT_INIT_FILE"
}

# Unseal Vault
unseal_vault() {
    log "Unsealing Vault..."

    if [[ ! -f "$VAULT_INIT_FILE" ]]; then
        error "Vault initialization file not found: $VAULT_INIT_FILE"
    fi

    # Extract unseal keys
    UNSEAL_KEY_1=$(jq -r '.unseal_keys_b64[0]' "$VAULT_INIT_FILE")
    UNSEAL_KEY_2=$(jq -r '.unseal_keys_b64[1]' "$VAULT_INIT_FILE")
    UNSEAL_KEY_3=$(jq -r '.unseal_keys_b64[2]' "$VAULT_INIT_FILE")

    # Validate unseal keys were extracted
    if [[ -z "$UNSEAL_KEY_1" || "$UNSEAL_KEY_1" == "null" ]]; then
        error "Failed to extract unseal keys from init file"
    fi

    # Unseal with threshold keys
    vault operator unseal "$UNSEAL_KEY_1" || error "Failed to apply unseal key 1"
    vault operator unseal "$UNSEAL_KEY_2" || error "Failed to apply unseal key 2"
    vault operator unseal "$UNSEAL_KEY_3" || error "Failed to apply unseal key 3"

    log "Vault unsealed successfully"
}

# Authenticate with root token
authenticate_vault() {
    log "Authenticating with Vault..."

    if [[ ! -f "$VAULT_INIT_FILE" ]]; then
        error "Vault initialization file not found: $VAULT_INIT_FILE"
    fi

    ROOT_TOKEN=$(jq -r '.root_token' "$VAULT_INIT_FILE")
    vault login "$ROOT_TOKEN"

    log "Authenticated with Vault successfully"
}

# Enable audit logging
enable_audit_logging() {
    log "Enabling audit logging..."

    # Enable file audit device
    vault audit enable file file_path=/opt/vault/logs/vault-audit.log

    # Enable syslog audit device
    vault audit enable syslog tag="vault" facility="AUTH"

    log "Audit logging enabled"
}

# Enable secret engines
enable_secret_engines() {
    log "Enabling secret engines..."

    # Enable KV v2 secret engine
    vault secrets enable -path=secret kv-v2

    # Enable PKI secret engine for certificates
    vault secrets enable -path=pki pki
    vault secrets tune -max-lease-ttl=87600h pki

    # Enable database secret engine
    vault secrets enable database

    # Enable transit secret engine for encryption
    vault secrets enable transit

    log "Secret engines enabled"
}

# Configure PKI
configure_pki() {
    log "Configuring PKI..."

    # Generate root CA
    vault write pki/root/generate/internal \
        common_name="RiskOptimizer Root CA" \
        ttl=87600h

    # Configure CA and CRL URLs
    vault write pki/config/urls \
        issuing_certificates="$VAULT_ADDR/v1/pki/ca" \
        crl_distribution_points="$VAULT_ADDR/v1/pki/crl"

    # Create role for RiskOptimizer applications
    vault write pki/roles/riskoptimizer-app \
        allowed_domains="riskoptimizer.com,riskoptimizer.local" \
        allow_subdomains=true \
        max_ttl=72h

    log "PKI configured"
}

# Create policies
create_policies() {
    log "Creating Vault policies..."

    # Create admin policy
    vault policy write admin - <<EOF
path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
path "sys/auth/*" {
  capabilities = ["create", "update", "delete", "sudo"]
}
path "sys/policies/acl/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
EOF

    # Create application policy
    vault policy write riskoptimizer-app - <<EOF
path "secret/data/riskoptimizer/app/*" {
  capabilities = ["read"]
}
path "database/creds/riskoptimizer-app" {
  capabilities = ["read"]
}
path "pki/issue/riskoptimizer-app" {
  capabilities = ["create", "update"]
}
EOF

    # Create DevOps policy
    vault policy write riskoptimizer-devops - <<EOF
path "secret/data/riskoptimizer/devops/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "auth/kubernetes/role/riskoptimizer-*" {
  capabilities = ["read", "update"]
}
EOF

    log "Policies created"
}

# Enable authentication methods
enable_auth_methods() {
    log "Enabling authentication methods..."

    # Enable Kubernetes auth method
    vault auth enable kubernetes

    # Enable LDAP auth method for enterprise integration
    vault auth enable ldap

    # Enable AppRole auth method for applications
    vault auth enable approle

    log "Authentication methods enabled"
}

# Main execution
main() {
    log "Starting Vault initialization process..."

    # Check if Vault is already initialized
    if ! check_vault_status; then
        initialize_vault
        unseal_vault
        authenticate_vault
    else
        log "Vault is already initialized, skipping initialization"
        # Still need to authenticate for configuration
        authenticate_vault
    fi

    # Configure Vault
    enable_audit_logging
    enable_secret_engines
    configure_pki
    create_policies
    enable_auth_methods

    log "Vault initialization and configuration completed successfully!"
    warn "Remember to:"
    warn "1. Securely store the unseal keys and root token"
    warn "2. Configure authentication methods for your environment"
    warn "3. Set up regular backup procedures"
    warn "4. Monitor audit logs for security events"
}

# Run main function
main "$@"
