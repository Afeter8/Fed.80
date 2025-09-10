#!/usr/bin/env python3
# Simple webhook receiver for ClouDNS webhooks & GitHub pushes
from flask import Flask, request, jsonify
import os, subprocess, threading

app = Flask(__name__)

# ruta hacia scripts locales
ROTATE_SCRIPT = "/opt/star-tigo-defensa/rotate/rotate_service.py"
REPAIR_SCRIPT = "/opt/star-tigo-defensa/repair/monitor_and_repair.py"
SYNC_SCRIPT = "/opt/star-tigo-defensa/sync/sync_repos.sh"

def async_run(cmd):
    threading.Thread(target=subprocess.run, args=(cmd,), kwargs={"shell":True}).start()

@app.route("/webhook/cloudns", methods=["POST"])
def cloudns_webhook():
    data = request.json or {}
    # data contiene info del check (status Up/Down, id, etc.)
    # por ejemplo: si check Down -> forzar reparación / advertir
    status = data.get("status")
    check_name = data.get("name")
    if status and status.lower() == "down":
        # registrar y lanzar reparación automática
        async_run(f"python3 {REPAIR_SCRIPT} &")
    return jsonify({"ok":True})

@app.route("/webhook/github", methods=["POST"])
def github_webhook():
    # on push -> actualizar sync y/o disparar rotate
    async_run(f"bash {SYNC_SCRIPT} &")
    async_run(f"python3 {ROTATE_SCRIPT} &")
    return jsonify({"ok":True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
