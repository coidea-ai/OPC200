# OPC200 Customer Template
# This directory contains templates for new customer initialization

# Directory structure that will be created:
#
# customers/{mode}/{OPC_ID}/
# ├── deployment/              # Deployment configurations
# │   ├── gateway.yml         # Gateway configuration
# │   ├── docker-compose.yml  # Service orchestration
# │   └── env                 # Environment variables
# │
# ├── data-vault/             # Encrypted data storage
# │   ├── encrypted/          # Encrypted files
# │   ├── local-only/         # Data that never leaves local
# │   └── audit-trail/        # Access logs
# │       ├── access-logs/
# │       ├── sync-logs/
# │       └── emergency-access/
# │
# ├── tailscale/              # VPN configuration
# │   ├── node-info.yml
# │   └── auth-key            # Secure auth key (chmod 600)
# │
# ├── remote-sessions/        # Remote support session logs
# │
# ├── sync-status/            # Synchronization status
# │
# └── compliance/             # Compliance documentation
#     ├── data-residency.yml
#     ├── encryption-manifest.yml
#     └── audit-reports/

# This template is used by scripts/setup/customer-init.sh
