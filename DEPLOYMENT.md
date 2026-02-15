# BTC Dashboard Deployment Script

## Overview

`run.sh` is a production-ready deployment script for the BTC Dashboard application. It automates the deployment process by pulling the latest code, updating dependencies, and restarting the service.

## Features

- **Safe & Idempotent**: Safe to run multiple times without side effects
- **Fail-Fast**: Exits immediately on errors with clear error messages
- **Comprehensive Logging**: Timestamps and logs all operations to `deployment.log`
- **Smart Dependency Management**: Only reinstalls dependencies when `requirements.txt` changes
- **Environment Validation**: Checks all prerequisites before making any changes
- **Configurable**: Key settings can be overridden via environment variables

## Prerequisites

### 1. System Requirements

- Ubuntu/Debian-like Linux system
- Python 3.x installed
- Git repository initialized
- systemd (for service management)
- Appropriate permissions (script may require `sudo` for systemctl commands)

### 2. Systemd Service Setup

Before running `run.sh`, you need to create a systemd service for the BTC Dashboard:

#### Step 1: Create the service file

```bash
sudo nano /etc/systemd/system/btc-dashboard.service
```

#### Step 2: Add service configuration

Use the provided `btc-dashboard.service.example` as a template, adjusting paths:

```ini
[Unit]
Description=BTC Dashboard Streamlit Application
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/btc-dashboard
Environment="PATH=/path/to/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/path/to/.venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1
Restart=always
RestartSec=10

# Security hardening
PrivateTmp=yes
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/path/to/btc-dashboard

[Install]
WantedBy=multi-user.target
```

**Important**: Replace `/path/to/btc-dashboard` and `/path/to/.venv/bin` with actual paths.

#### Step 3: Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable btc-dashboard.service
sudo systemctl start btc-dashboard.service
sudo systemctl status btc-dashboard.service
```

## Usage

### Basic Usage

```bash
sudo ./run.sh
```

### With Custom Configuration

You can override default settings using environment variables:

```bash
# Use a different service name
SERVICE_NAME=my-btc-service ./run.sh

# Use a specific Python binary
PYTHON_BIN=/usr/bin/python3.11 ./run.sh

# Pull from a different branch
GIT_BRANCH=develop ./run.sh

# Combine multiple overrides
SERVICE_NAME=my-btc-service GIT_BRANCH=develop ./run.sh
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `btc-dashboard.service` | Name of the systemd service |
| `PYTHON_BIN` | `python3` | Python executable to use |
| `GIT_BRANCH` | `main` | Git branch to pull from |

## What the Script Does

### 1. Pre-Deployment Validation

- Verifies git repository exists
- Checks Python installation
- Validates `requirements.txt` exists
- Confirms systemd service is configured

### 2. Code Update

- Stashes any local changes (if present)
- Fetches latest changes from remote
- Pulls latest code from specified branch

### 3. Dependency Management

- Calculates MD5 checksum of `requirements.txt`
- Compares with previous checksum
- Only reinstalls dependencies if requirements changed
- Saves new checksum for future runs

### 4. Service Restart

- Checks if service is running
- Restarts (or starts) the systemd service
- Verifies service started successfully
- Shows current service status

## Logging

All operations are logged with timestamps to `deployment.log` in the repository root:

```bash
# View recent deployment logs
tail -f deployment.log

# View all deployment history
cat deployment.log
```

## Troubleshooting

### "Not a git repository" Error

**Problem**: Script must be run from the repository root.

**Solution**:
```bash
cd /path/to/btc-dashboard
./run.sh
```

### "Systemd service not found" Error

**Problem**: The systemd service hasn't been created.

**Solution**: Follow the [Systemd Service Setup](#2-systemd-service-setup) instructions above.

### "Service failed to start" Error

**Problem**: The service configuration may be incorrect.

**Solution**: Check service logs:
```bash
sudo journalctl -u btc-dashboard.service -n 50 --no-pager
```

### Permission Denied

**Problem**: Script requires elevated privileges for systemctl commands.

**Solution**: Run with sudo:
```bash
sudo ./run.sh
```

## Automation with Cron

To automate deployments, add to crontab:

```bash
# Edit crontab
sudo crontab -e

# Add line to run deployment daily at 2 AM
0 2 * * * cd /path/to/btc-dashboard && ./run.sh >> /var/log/btc-deployment-cron.log 2>&1
```

## Security Considerations

- The script uses `set -euo pipefail` for safe error handling
- Local changes are stashed (not discarded) before pulling
- Dependency installation is tracked via checksums
- Service runs with limited privileges (as configured in systemd)
- All operations are logged for audit purposes

## Testing

### Dry-Run Validation

You can test the validation checks without making changes:

```bash
# Test bash syntax
bash -n run.sh

# Run validation checks only (will fail at systemd check if not configured)
./run.sh 2>&1 | head -20
```

## Best Practices

1. **Test First**: Test the script in a staging environment before production
2. **Review Logs**: Check `deployment.log` after each run
3. **Monitor Service**: Use `systemctl status` to verify service health
4. **Backup Configuration**: Keep backups of your systemd service file
5. **Version Control**: Commit any local configuration changes before running

## Support

For issues or questions:
- Check `deployment.log` for detailed error messages
- Review systemd logs: `sudo journalctl -u btc-dashboard.service`
- Verify service configuration: `sudo systemctl cat btc-dashboard.service`

## License

This deployment script is part of the BTC Dashboard project.
