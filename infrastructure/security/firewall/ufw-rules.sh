#!/bin/bash
# UFW Firewall Rules for RiskOptimizer Infrastructure
set -euo pipefail

# Reset and set defaults
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw default deny forward

# SSH (restrict to management networks only)
ufw allow from 10.0.0.0/8    to any port 22 proto tcp comment 'SSH from RFC1918'
ufw allow from 172.16.0.0/12 to any port 22 proto tcp comment 'SSH from RFC1918'
ufw allow from 192.168.0.0/16 to any port 22 proto tcp comment 'SSH from RFC1918'

# SSH rate limiting (after the allow rules so they are not overridden)
ufw limit ssh comment 'Rate limit SSH'

# HTTP/HTTPS (public)
ufw allow 80/tcp  comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Vault API (internal only)
ufw allow from 10.0.0.0/8    to any port 8200 proto tcp comment 'Vault API'
ufw allow from 172.16.0.0/12 to any port 8200 proto tcp comment 'Vault API'
# Vault cluster port
ufw allow from 10.0.0.0/8    to any port 8201 proto tcp comment 'Vault cluster'

# PostgreSQL (application subnets only, NOT MySQL 3306)
ufw allow from 10.0.11.0/24 to any port 5432 proto tcp comment 'PostgreSQL from private subnet 1'
ufw allow from 10.0.12.0/24 to any port 5432 proto tcp comment 'PostgreSQL from private subnet 2'
ufw allow from 10.0.13.0/24 to any port 5432 proto tcp comment 'PostgreSQL from private subnet 3'

# Redis (application subnets only)
ufw allow from 10.0.11.0/24 to any port 6379 proto tcp comment 'Redis from private subnet 1'
ufw allow from 10.0.12.0/24 to any port 6379 proto tcp comment 'Redis from private subnet 2'
ufw allow from 10.0.13.0/24 to any port 6379 proto tcp comment 'Redis from private subnet 3'

# Kubernetes API server
ufw allow from 10.0.0.0/8 to any port 6443 proto tcp comment 'Kubernetes API'

# Kubernetes node ports (kubelet, scheduler, controller-manager)
ufw allow from 10.0.0.0/8 to any port 10250 proto tcp comment 'Kubelet API'
# Remove 10251/10252 - these are deprecated; scheduler/controller now use 10259/10257
ufw allow from 10.0.0.0/8 to any port 10257 proto tcp comment 'kube-controller-manager'
ufw allow from 10.0.0.0/8 to any port 10259 proto tcp comment 'kube-scheduler'

# etcd
ufw allow from 10.0.0.0/8 to any port 2379:2380 proto tcp comment 'etcd'

# Monitoring (internal monitoring subnet)
ufw allow from 10.0.0.0/8 to any port 9090 proto tcp comment 'Prometheus'
ufw allow from 10.0.0.0/8 to any port 9100 proto tcp comment 'Node Exporter'
ufw allow from 10.0.0.0/8 to any port 3001 proto tcp comment 'Grafana'
ufw allow from 10.0.0.0/8 to any port 9200 proto tcp comment 'Elasticsearch'
ufw allow from 10.0.0.0/8 to any port 5601 proto tcp comment 'Kibana'

# Application backend
ufw allow from 10.0.0.0/8 to any port 8080 proto tcp comment 'App backend HTTP'
ufw allow from 10.0.0.0/8 to any port 8081 proto tcp comment 'App metrics'
ufw allow from 10.0.0.0/8 to any port 8082 proto tcp comment 'App health'

# Enable UFW and turn on logging
ufw logging medium
ufw --force enable

echo "UFW rules applied successfully"
ufw status verbose
