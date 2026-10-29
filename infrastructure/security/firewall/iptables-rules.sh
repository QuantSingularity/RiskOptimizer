#!/bin/bash

# Advanced iptables configuration for RiskOptimizer infrastructure
# This script provides more granular control than UFW

set -euo pipefail

# Flush existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

# Set default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback traffic
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established and related connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# Drop INVALID packets
iptables -A INPUT -m conntrack --ctstate INVALID -j DROP
iptables -A OUTPUT -m conntrack --ctstate INVALID -j DROP


# Rate limiting for SSH (prevent brute force)
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSH
iptables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Allow Vault access from specific networks
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 8200 -j ACCEPT
iptables -A INPUT -p tcp -s 172.16.0.0/12 --dport 8200 -j ACCEPT

# Database access (PostgreSQL and MySQL)
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 5432 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 3306 -j ACCEPT

# Redis access
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 6379 -j ACCEPT

# Kubernetes cluster communication
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 6443 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 10250 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 10251 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 10252 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.0.0/8 --dport 2379:2380 -j ACCEPT

# Monitoring services
iptables -A INPUT -p tcp -s 10.0.2.0/24 --dport 9090 -j ACCEPT  # Prometheus
iptables -A INPUT -p tcp -s 10.0.2.0/24 --dport 3000 -j ACCEPT  # Grafana
iptables -A INPUT -p tcp -s 10.0.2.0/24 --dport 9200 -j ACCEPT  # Elasticsearch
iptables -A INPUT -p tcp -s 10.0.2.0/24 --dport 5601 -j ACCEPT  # Kibana

# Application ports
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 8080 -j ACCEPT
iptables -A INPUT -p tcp -s 10.0.1.0/24 --dport 8000 -j ACCEPT

# ICMP (ping) - limited
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT

# Log dropped packets (for security monitoring)
iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables-dropped: " --log-level 4

# Drop everything else
iptables -A INPUT -j DROP

# Save rules (Ubuntu/Debian)
if command -v iptables-save >/dev/null 2>&1; then
    iptables-save > /etc/iptables/rules.v4
fi

# Save rules (CentOS/RHEL)
if command -v service >/dev/null 2>&1; then
    service iptables save
fi

echo "iptables rules applied successfully"

# Apply equivalent rules for IPv6
if command -v ip6tables &>/dev/null; then
    ip6tables -F
    ip6tables -X
    ip6tables -P INPUT DROP
    ip6tables -P FORWARD DROP
    ip6tables -P OUTPUT ACCEPT
    ip6tables -A INPUT -i lo -j ACCEPT
    ip6tables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    ip6tables -A INPUT -m conntrack --ctstate INVALID -j DROP
    ip6tables -A INPUT -p ipv6-icmp -j ACCEPT
    ip6tables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --set --name SSHv6
    ip6tables -A INPUT -p tcp --dport 22 -m conntrack --ctstate NEW -m recent --update --seconds 60 --hitcount 4 --name SSHv6 -j DROP
    ip6tables -A INPUT -p tcp --dport 22 -j ACCEPT
    ip6tables -A INPUT -p tcp --dport 80 -j ACCEPT
    ip6tables -A INPUT -p tcp --dport 443 -j ACCEPT
    ip6tables -A INPUT -j DROP
    if command -v ip6tables-save &>/dev/null; then
        ip6tables-save > /etc/iptables/rules.v6
    fi
fi
