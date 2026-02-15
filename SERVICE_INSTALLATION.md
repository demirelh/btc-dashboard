# BTC Dashboard - Systemd Service Installation Guide

This guide explains how to install and configure the `btc-dashboard.service` systemd service for production deployment.

## Prerequisites

- Ubuntu/Debian-like Linux system with systemd
- Python 3.x installed (tested with Python 3.13.5)
- BTC Dashboard repository cloned to `/home/pi/btc-dashboard`
- User `pi` with appropriate permissions

## Quick Installation

### Automated Installation (Recommended)

The easiest way to install the service is using the provided installation script:

```bash
cd /home/pi/btc-dashboard
sudo ./install-service.sh
```

The script will automatically:
- Check system prerequisites (Python, systemd)
- Install Python dependencies if not already present
- Install and configure the systemd service
- Enable auto-start on boot
- Start the service

### Manual Installation

Alternatively, you can install manually:

```bash
# 1. Install Python dependencies
python3 -m pip install -r requirements.txt

# 2. Copy the service file to systemd directory
sudo cp /home/pi/btc-dashboard/btc-dashboard.service /etc/systemd/system/

# 3. Reload systemd to recognize the new service
sudo systemctl daemon-reload

# 4. Enable the service to start on boot
sudo systemctl enable btc-dashboard.service

# 5. Start the service immediately
sudo systemctl start btc-dashboard.service

# 6. Verify the service is running
sudo systemctl status btc-dashboard.service
```

## Verification

After installation, verify the service is working correctly:

### Check Service Status
```bash
sudo systemctl status btc-dashboard.service
```

Expected output:
```
● btc-dashboard.service - BTC Dashboard Streamlit Application
     Loaded: loaded (/etc/systemd/system/btc-dashboard.service; enabled; vendor preset: enabled)
     Active: active (running) since [date]
```

### View Service Logs
```bash
# View recent logs
sudo journalctl -u btc-dashboard.service -n 50

# Follow logs in real-time
sudo journalctl -u btc-dashboard.service -f

# View logs since last boot
sudo journalctl -u btc-dashboard.service -b
```

### Test Web Interface
The Streamlit application should be accessible at:
```
http://127.0.0.1:8501
```

For external HTTPS access through a reverse proxy (e.g., https://lnodebtc.duckdns.org/), see [REVERSE_PROXY_SETUP.md](./REVERSE_PROXY_SETUP.md).

## Service Configuration Details

### Service Properties

| Property | Value | Description |
|----------|-------|-------------|
| **User** | `pi` | User account running the service |
| **Working Directory** | `/home/pi/btc-dashboard` | Application root directory |
| **ExecStart** | `python3 -m streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false` | Command to start the application with reverse proxy support |
| **Port** | `8501` | Streamlit default port |
| **Address** | `127.0.0.1` | Binds to localhost only (secure by default) |
| **Restart** | `always` | Automatically restarts on failure |
| **RestartSec** | `10` | Wait 10 seconds before restart |

### Security Features

The service includes several security hardening features:

- **PrivateTmp=yes**: Isolated /tmp directory
- **NoNewPrivileges=true**: Cannot gain new privileges
- **ProtectSystem=strict**: Read-only access to /usr, /boot, /efi
- **ProtectHome=read-only**: Limited home directory access
- **ReadWritePaths**: Write access only to application directory

## Common Operations

### Start the Service
```bash
sudo systemctl start btc-dashboard.service
```

### Stop the Service
```bash
sudo systemctl stop btc-dashboard.service
```

### Restart the Service
```bash
sudo systemctl restart btc-dashboard.service
```

### Enable Auto-Start on Boot
```bash
sudo systemctl enable btc-dashboard.service
```

### Disable Auto-Start on Boot
```bash
sudo systemctl disable btc-dashboard.service
```

### View Service Configuration
```bash
sudo systemctl cat btc-dashboard.service
```

## Integration with run.sh

The deployment script `run.sh` automatically manages the service:

```bash
# Deploy latest code and restart service
sudo ./run.sh
```

The script will:
1. Pull latest code from git
2. Update Python dependencies (if requirements.txt changed)
3. Restart the systemd service
4. Verify service is running

## Troubleshooting

### Service Fails to Start

**Check logs for error details:**
```bash
sudo journalctl -u btc-dashboard.service -n 100 --no-pager
```

**Common issues:**

1. **Port already in use (8501)**
   ```bash
   # Check what's using the port
   sudo netstat -tulpn | grep 8501
   # or
   sudo lsof -i :8501
   ```

2. **Python dependencies missing**

   If you used the automated installation script (`install-service.sh`), dependencies should already be installed. If you installed manually or encounter this error, install them with:
   ```bash
   cd /home/pi/btc-dashboard
   python3 -m pip install -r requirements.txt
   ```

3. **Data file missing (btc.json)**
   ```bash
   cd /home/pi/btc-dashboard
   python3 update.py
   ```

4. **Permission issues**
   ```bash
   # Ensure pi user owns the directory
   sudo chown -R pi:pi /home/pi/btc-dashboard
   ```

### Service Starts but Web Interface Not Accessible

1. **Check if service is listening:**
   ```bash
   sudo netstat -tulpn | grep 8501
   ```

2. **Test locally:**
   ```bash
   curl http://127.0.0.1:8501
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status
   ```

### Service Keeps Restarting

**Check for application errors:**
```bash
sudo journalctl -u btc-dashboard.service -f
```

Common causes:
- Missing Python dependencies
- Invalid configuration in code
- Port conflict
- File permission issues

### Logs Not Showing Up

**Verify journald is working:**
```bash
sudo systemctl status systemd-journald
```

**Check journal size:**
```bash
sudo journalctl --disk-usage
```

## Advanced Configuration

### Change Port or Address

Edit `/etc/systemd/system/btc-dashboard.service`:

```ini
# Allow external access (be careful with security!)
ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true

# Use different port
ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port=8080 --server.address=127.0.0.1 --server.headless=true
```

After changes, reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart btc-dashboard.service
```

### Use Virtual Environment

If you want to use a Python virtual environment:

1. Create .venv:
   ```bash
   cd /home/pi/btc-dashboard
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Update service file (`/etc/systemd/system/btc-dashboard.service`):
   ```ini
   Environment="PATH=/home/pi/btc-dashboard/.venv/bin:/usr/local/bin:/usr/bin:/bin"
   ExecStart=/home/pi/btc-dashboard/.venv/bin/python -m streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true
   ```

3. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart btc-dashboard.service
   ```

### Environment Variables

If you need to set environment variables (e.g., for API keys):

1. Create environment file:
   ```bash
   sudo nano /etc/btc-dashboard-env
   ```

2. Add variables:
   ```ini
   BTC_UPDATE_TOKEN=your-token-here
   OTHER_VAR=value
   ```

3. Update service file:
   ```ini
   EnvironmentFile=/etc/btc-dashboard-env
   ```

4. Reload and restart:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart btc-dashboard.service
   ```

## Uninstallation

To completely remove the service:

```bash
# Stop and disable the service
sudo systemctl stop btc-dashboard.service
sudo systemctl disable btc-dashboard.service

# Remove service file
sudo rm /etc/systemd/system/btc-dashboard.service

# Reload systemd
sudo systemctl daemon-reload
```

## Monitoring and Maintenance

### Check Service Health
```bash
# Service status
sudo systemctl is-active btc-dashboard.service

# Service enabled on boot?
sudo systemctl is-enabled btc-dashboard.service

# Full status
sudo systemctl status btc-dashboard.service
```

### Monitor Resource Usage
```bash
# CPU and memory usage
sudo systemctl status btc-dashboard.service | grep -E "Memory|CPU"

# Or use top/htop
top -u pi
```

### Log Rotation

Systemd journal automatically rotates logs. Configure in `/etc/systemd/journald.conf`:

```ini
[Journal]
SystemMaxUse=100M
MaxRetentionSec=7day
```

## Security Best Practices

1. **Keep localhost binding** (127.0.0.1) unless you need external access
2. **Use reverse proxy** (nginx/apache) for external access with HTTPS
3. **Regular updates**: Keep Python and dependencies updated
4. **Monitor logs**: Check for suspicious activity
5. **Firewall**: Use ufw or iptables to restrict access
6. **Don't run as root**: Service runs as user `pi` (non-privileged)

## Testing in Development

Before deploying to production, test locally:

```bash
# Test the ExecStart command manually
cd /home/pi/btc-dashboard
python3 -m streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true
```

Press Ctrl+C to stop, then install the service.

## Support

For issues:
1. Check service logs: `sudo journalctl -u btc-dashboard.service -n 100`
2. Verify Python dependencies: `pip list`
3. Test manual startup: `python3 -m streamlit run app.py`
4. Check system resources: `df -h` and `free -h`

## Summary

The systemd service provides:
- ✅ Automatic startup on boot
- ✅ Automatic restart on failure
- ✅ Centralized logging via journald
- ✅ Service management via systemctl
- ✅ Security hardening
- ✅ Integration with deployment script

After installation, use `sudo ./run.sh` for deployments.
