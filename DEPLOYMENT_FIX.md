# DEPLOYMENT ERROR FIX - Systemd Service Not Found

## Problem
The deployment script `/home/pi/btc-dashboard/run.sh` fails with:
```
ERROR: Systemd service 'btc-dashboard.service' not found
```

## Root Cause
The systemd service file exists in the repository but has **not been installed** to the system directory where systemd can find it (`/etc/systemd/system/`).

## IMMEDIATE FIX - Run These Commands on the Server

SSH into your server as the `pi` user and run:

```bash
# Navigate to the application directory
cd /home/pi/btc-dashboard

# Method 1: Use the automated installation script (RECOMMENDED)
sudo ./install-service.sh
```

**OR** if you prefer manual installation:

```bash
# Method 2: Manual installation
# Copy service file to systemd directory
sudo cp /home/pi/btc-dashboard/btc-dashboard.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable btc-dashboard.service

# Start the service immediately
sudo systemctl start btc-dashboard.service

# Verify the service is running
sudo systemctl status btc-dashboard.service
```

## Verification Checklist

After installation, verify everything works:

### 1. Check Service Status
```bash
sudo systemctl status btc-dashboard.service
```

**Expected output:**
```
● btc-dashboard.service - BTC Dashboard Streamlit Application
     Loaded: loaded (/etc/systemd/system/btc-dashboard.service; enabled)
     Active: active (running) since [date]
```

### 2. View Service Logs
```bash
# View recent logs
sudo journalctl -u btc-dashboard.service -n 50

# Follow logs in real-time (Ctrl+C to exit)
sudo journalctl -u btc-dashboard.service -f
```

**Look for:**
- Streamlit startup messages
- No error messages
- "You can now view your Streamlit app in your browser"

### 3. Verify run.sh Now Works
```bash
cd /home/pi/btc-dashboard
sudo ./run.sh
```

**Expected:**
- ✓ Git repository validated
- ✓ Python found
- ✓ requirements.txt found
- ✓ Systemd service 'btc-dashboard.service' found
- ✓ Service restarted successfully

### 4. Test Web Interface
```bash
# From the server
curl http://127.0.0.1:8501
```

Should return HTML content (Streamlit app).

## Technical Details

### Service Configuration
The installed service (`btc-dashboard.service`) is configured with:

| Setting | Value | Description |
|---------|-------|-------------|
| **User** | `pi` | Service runs as the pi user |
| **Working Directory** | `/home/pi/btc-dashboard` | Application root |
| **ExecStart** | `/usr/bin/python3 -m streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true` | Start command |
| **Port** | `8501` | Streamlit default port |
| **Restart** | `always` | Auto-restart on failure |
| **Python** | System Python3 | No virtualenv used |

### Start Command Explanation
```bash
/usr/bin/python3 -m streamlit run app.py \
  --server.port=8501 \
  --server.address=127.0.0.1 \
  --server.headless=true
```

- **`/usr/bin/python3`**: System Python 3 interpreter
- **`-m streamlit`**: Run streamlit as a module
- **`run app.py`**: Start Streamlit with app.py as entry point
- **`--server.port=8501`**: Listen on port 8501
- **`--server.address=127.0.0.1`**: Bind to localhost only (secure)
- **`--server.headless=true`**: Run in headless mode (no browser popup)

### No Virtual Environment
The service uses **system Python 3** directly. No virtualenv is configured because:
1. The `btc-dashboard.service` file uses `/usr/bin/python3`
2. The `Environment="PATH=..."` does not include a .venv path
3. Dependencies are installed system-wide via `pip install -r requirements.txt`

If you want to use a virtualenv in the future, see the "Advanced Configuration" section in `SERVICE_INSTALLATION.md`.

## What Each File Does

### `btc-dashboard.service`
- **Location in repo**: `/home/pi/btc-dashboard/btc-dashboard.service`
- **Install location**: `/etc/systemd/system/btc-dashboard.service`
- **Purpose**: Systemd unit file that defines how to run the application as a service
- **Configured for**: Production deployment on `/home/pi/btc-dashboard` with user `pi`

### `install-service.sh`
- **Purpose**: Automated script to install and start the systemd service
- **What it does**:
  1. Validates prerequisites (root access, systemd, Python)
  2. Backs up existing service if present
  3. Copies service file to `/etc/systemd/system/`
  4. Reloads systemd daemon
  5. Enables service for auto-start on boot
  6. Starts the service immediately
  7. Verifies successful startup

### `run.sh`
- **Purpose**: Production deployment script
- **What it does**:
  1. Pulls latest code from git
  2. Updates Python dependencies (if requirements.txt changed)
  3. Restarts the systemd service
  4. Verifies service is running
- **Requirement**: Expects `btc-dashboard.service` to be installed

## Troubleshooting

### Service Fails to Start

**Check logs:**
```bash
sudo journalctl -u btc-dashboard.service -n 100 --no-pager
```

**Common issues:**

1. **Port 8501 already in use:**
   ```bash
   sudo netstat -tulpn | grep 8501
   # or
   sudo lsof -i :8501
   ```
   Solution: Stop the other process or change the port in the service file.

2. **Python dependencies missing:**
   ```bash
   cd /home/pi/btc-dashboard
   python3 -m pip install -r requirements.txt
   ```

3. **Permission issues:**
   ```bash
   sudo chown -R pi:pi /home/pi/btc-dashboard
   ```

4. **Data file missing:**
   ```bash
   cd /home/pi/btc-dashboard
   python3 update.py
   ```

### Service Installed but run.sh Still Fails

**Verify service is visible to systemctl:**
```bash
systemctl list-unit-files | grep btc-dashboard
```

**Expected output:**
```
btc-dashboard.service    enabled    enabled
```

If not listed, the service file wasn't copied correctly. Re-run installation.

### After Fix: Test Full Deployment

Once the service is installed, test the complete deployment workflow:

```bash
cd /home/pi/btc-dashboard

# Run deployment script
sudo ./run.sh

# Should complete without errors and show:
# ✓ Systemd service 'btc-dashboard.service' found
# ✓ Service 'btc-dashboard.service' is running
# Deployment completed successfully!
```

## Summary

**The fix is simple:**
1. Run `sudo ./install-service.sh` on the server
2. Verify with `sudo systemctl status btc-dashboard.service`
3. Test with `sudo ./run.sh`

**Why this happened:**
- The repository contains the service file
- But systemd looks for service files in `/etc/systemd/system/`
- The file needs to be **copied** to that system directory
- The `install-service.sh` script automates this process

**After the fix:**
- ✅ Service is installed and running
- ✅ Service auto-starts on boot
- ✅ `run.sh` deployment script works
- ✅ Application accessible at http://127.0.0.1:8501

## Additional Documentation

For more details, see:
- **SERVICE_INSTALLATION.md**: Complete systemd service guide
- **DEPLOYMENT.md**: Deployment script documentation
- **README.md**: General project overview
