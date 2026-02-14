# QUICK FIX - Service Not Found Error

## The Problem
```
ERROR: Systemd service 'btc-dashboard.service' not found
```

## The Solution (Run on Server)

```bash
# SSH to your server and run:
cd /home/pi/btc-dashboard
sudo ./install-service.sh
```

That's it! The script will:
- ✅ Install the systemd service
- ✅ Enable auto-start on boot
- ✅ Start the service immediately
- ✅ Verify it's running

## Verify It Works

```bash
# Check service status
sudo systemctl status btc-dashboard.service

# View logs
sudo journalctl -u btc-dashboard.service -n 50

# Test deployment script
sudo ./run.sh
```

## What Was the Issue?

The service file exists in the repository but wasn't installed to `/etc/systemd/system/` where systemd looks for it. The `install-service.sh` script copies it to the correct location.

## For Complete Details

See `DEPLOYMENT_FIX.md` for:
- Manual installation steps
- Service configuration details
- Troubleshooting guide
- Verification checklist
