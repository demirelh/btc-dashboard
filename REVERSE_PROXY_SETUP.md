# Reverse Proxy Setup for HTTPS Access

This document explains how the BTC Dashboard is configured to work behind a reverse proxy (Caddy) for HTTPS access via `https://lnodebtc.duckdns.org/`.

## Architecture

```
Internet (HTTPS)
    ↓
Caddy Reverse Proxy (port 443)
    ↓ (HTTP)
Streamlit App (localhost:8501)
```

## Streamlit Configuration for Reverse Proxy

When Streamlit runs behind a reverse proxy that handles HTTPS termination, specific settings are required:

### 1. `.streamlit/config.toml`

```toml
[server]
headless = true
port = 8501
# Disable CORS checks - proxy handles this
enableCORS = false
# Disable XSRF protection - proxy handles this
enableXsrfProtection = false
```

### 2. `btc-dashboard.service`

The systemd service includes the same flags:

```bash
ExecStart=/usr/bin/python3 -m streamlit run app.py \
  --server.port=8501 \
  --server.address=127.0.0.1 \
  --server.headless=true \
  --server.enableCORS=false \
  --server.enableXsrfProtection=false
```

## Why These Settings?

### `enableCORS = false`

When CORS is enabled, Streamlit checks the `Origin` header and may reject requests that come through the proxy. Since the proxy (Caddy) is handling the HTTPS connection and forwarding requests to Streamlit on localhost, disabling CORS allows the proxied requests to work properly.

### `enableXsrfProtection = false`

XSRF protection in Streamlit can interfere with requests coming through a reverse proxy because the origin validation may fail. The reverse proxy should handle security concerns like XSRF protection at its level.

## Caddy Configuration (Reference)

While the Caddyfile is not in this repository, a typical configuration for this setup would be:

```caddyfile
lnodebtc.duckdns.org {
    reverse_proxy localhost:8501 {
        # WebSocket support for Streamlit
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

## WebSocket Support

Streamlit uses WebSockets for real-time updates. The reverse proxy must support WebSocket connections and forward them to the Streamlit backend. Caddy handles this automatically.

## Security Notes

1. **Bind to localhost only**: The Streamlit app binds to `127.0.0.1:8501`, making it inaccessible from external networks. Only the reverse proxy can access it.

2. **HTTPS at proxy level**: All external traffic uses HTTPS (handled by Caddy), while internal communication between Caddy and Streamlit uses HTTP over localhost.

3. **Firewall**: Ensure your firewall only exposes ports 80 and 443, not port 8501.

## Troubleshooting

### Connection Refused or 502 Errors

- Check that Streamlit is running: `systemctl status btc-dashboard`
- Verify Streamlit is listening on localhost:8501: `netstat -tlnp | grep 8501`
- Check Caddy logs for proxy errors

### WebSocket Connection Failures

- Ensure Caddy is configured to proxy WebSocket connections
- Check browser console for WebSocket errors
- Verify `enableCORS=false` is set in Streamlit config

### CORS Errors in Browser Console

- Confirm `enableCORS=false` in both `.streamlit/config.toml` and service file
- Restart the service: `sudo systemctl restart btc-dashboard`
- Check that Caddy is forwarding headers correctly

## Testing the Setup

1. **Check Streamlit is running locally**:
   ```bash
   curl http://localhost:8501
   ```

2. **Check HTTPS access through proxy**:
   ```bash
   curl https://lnodebtc.duckdns.org/
   ```

3. **Check WebSocket connection**: Open the site in a browser and check the browser console for WebSocket connection status.

## Deployment

After making changes to the configuration:

1. Restart the Streamlit service:
   ```bash
   sudo systemctl restart btc-dashboard
   ```

2. Verify the service is running:
   ```bash
   sudo systemctl status btc-dashboard
   ```

3. Check the logs:
   ```bash
   sudo journalctl -u btc-dashboard -f
   ```
