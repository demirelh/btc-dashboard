from flask import Flask, jsonify, request
import os
import subprocess
import time

app = Flask(__name__)

TOKEN = os.environ.get("BTC_UPDATE_TOKEN", "")
PYTHON = "/home/pi/jupyterhub/venv/bin/python"
SCRIPT = "/home/pi/btc-dashboard/update.py"

@app.get("/api/health")
def health():
    return jsonify({"ok": True})

@app.post("/api/update")
def update():
    # Token-Schutz (nicht weglassen, wenn öffentlich erreichbar!)
    got = request.headers.get("X-Update-Token", "")
    if not TOKEN or got != TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    t0 = time.time()
    try:
        cp = subprocess.run(
            [PYTHON, SCRIPT],
            capture_output=True,
            text=True,
            timeout=300,
        )
        ok = (cp.returncode == 0)
        return jsonify({
            "ok": ok,
            "returncode": cp.returncode,
            "seconds": round(time.time() - t0, 2),
            "stdout_tail": cp.stdout[-2000:],
            "stderr_tail": cp.stderr[-2000:],
        }), (200 if ok else 500)
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "timeout"}), 504

if __name__ == "__main__":
    # nur lokal erreichbar, Caddy proxyt dann dahin
    app.run(host="127.0.0.1", port=9000)
