#!/usr/bin/env python3
# monitor_daemon.py
"""
Daemon de monitorización y respuesta segura (Vanguardia Titán).
- Ejecuta en bucle eterno.
- Monitorea endpoints (sentinel, ia, posts, governance).
- Si detecta anomalías: crea snapshot forense, firma, notifica y (opcional) invoca
  acciones de contención que requieren aprobación humana.
Requisitos:
  pip install requests python-dateutil
  gpg (opcional) para firmar snapshots
"""
from __future__ import annotations
import requests, os, time, json, hashlib, tarfile, subprocess
from datetime import datetime, timezone
from dateutil import parser as dateparser
from typing import Dict, Any

# ---------- CONFIG ----------
CONFIG = {
    "base_url": "http://127.0.0.1:5000",   # ajustar a tu API Flask
    "poll_interval": 20,                  # segundos entre poll
    "forensics_dir": "./forensics",
    "watch_endpoints": {
        "sentinel": "/api/sentinel/check",
        "ia": "/api/ia",
        "posts": "/api/posts",
        "governance": "/api/governance/status",
    },
    "notify_webhook": None,  # ejemplo: "https://hooks.slack.com/services/XXX/YYY/ZZZ"
    "gpg_sign_key": None,    # ejemplo: "admin@example.com" (opcional)
    "revocation_hook": None, # script/webhook para revocar claves/sesiones (debe requerir auth)
    "max_post_rate": 20,     # umbral simple: posts por 20s para alerta
}
# ---------- /CONFIG ----------

os.makedirs(CONFIG["forensics_dir"], exist_ok=True)

def now_ts():
    return datetime.now(timezone.utc).isoformat()

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk: break
            h.update(chunk)
    return h.hexdigest()

def notify(message: str, payload: Dict[str, Any]|None=None):
    print(f"[NOTIFY] {message}")
    if CONFIG["notify_webhook"]:
        try:
            requests.post(CONFIG["notify_webhook"], json={"text": message, "meta": payload or {}})
        except Exception as e:
            print("Notify failed:", e)

def save_forensic_snapshot(name_prefix: str, data_map: Dict[str, Any]):
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base = f"{name_prefix}_{ts}"
    folder = os.path.join(CONFIG["forensics_dir"], base)
    os.makedirs(folder, exist_ok=True)
    meta = {"timestamp": ts, "note": "snapshot from monitor daemon"}
    # Save JSON dumps
    for key, val in data_map.items():
        try:
            path = os.path.join(folder, f"{key}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(val, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Save JSON failed:", e)
    # Save metadata
    with open(os.path.join(folder, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    # Tar and sha256
    tar_path = os.path.join(CONFIG["forensics_dir"], base + ".tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(folder, arcname=os.path.basename(folder))
    sha = sha256_of_file(tar_path)
    with open(tar_path + ".sha256", "w") as f:
        f.write(sha)
    # Optional GPG sign
    if CONFIG["gpg_sign_key"]:
        try:
            subprocess.run(["gpg", "--batch", "--yes", "-u", CONFIG["gpg_sign_key"],
                            "--output", tar_path + ".sig", "--detach-sign", tar_path],
                           check=True)
        except Exception as e:
            print("GPG signing failed:", e)
    return {"folder": folder, "tar": tar_path, "sha256": sha}

def call_endpoint(path: str, method="GET", token=None):
    url = CONFIG["base_url"].rstrip("/") + path
    headers = {}
    if token: headers["Authorization"] = "Bearer " + token
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=10)
        else:
            r = requests.post(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Endpoint call failed {path}: {e}")
        return {"ok": False, "error": str(e)}

def basic_anomaly_checks(snapshot: Dict[str, Any]) -> Dict[str,Any]:
    alerts = []
    # sentinel: check integrity flags
    sent = snapshot.get("sentinel")
    if sent and "resultado" in sent:
        for rec in sent["resultado"]:
            if not rec.get("integridad_valida", True):
                alerts.append(f"Integridad rota: {rec.get('id')} {rec.get('nombre')}")
    # posts: sudden surge
    posts = snapshot.get("posts")
    if posts is not None:
        # count posts in last poll window
        now = datetime.utcnow()
        recent = 0
        for p in posts:
            try:
                t = dateparser.parse(p.get("fecha"))
                delta = (now - t).total_seconds()
                if delta <= CONFIG["poll_interval"]*3:
                    recent += 1
            except Exception:
                pass
        if recent >= CONFIG["max_post_rate"]:
            alerts.append(f"Alerta alta tasa de posts: {recent} posts recientes")
    # governance: suspicious (no votes allowed? depends)
    gov = snapshot.get("governance")
    if gov and (gov.get("favor",0) + gov.get("contra",0)) > 1000:
        alerts.append("Conteo de votos inusualmente alto")
    return {"alerts": alerts}

def request_containment_approval(forensic):
    # Crea una solicitud y notifica al equipo; retorno booleano: approved?
    msg = f"Solicitud de contención generada. Snapshot: {forensic['tar']}, sha256: {forensic['sha256']}. Aprobación requerida."
    notify(msg, {"forensic": forensic})
    # Aquí: implementación real debería crear ticket y esperar multi-approvals.
    # En este daemon devolvemos False (no ejecutar acciones destructivas automáticamente).
    return False

def take_safe_actions(snapshot):
    # Ejemplo: llamar a revocation hook (no destructivo) si configurado
    if CONFIG["revocation_hook"]:
        try:
            requests.post(CONFIG["revocation_hook"], json={"reason":"anomaly_detected", "timestamp": now_ts() }, timeout=8)
            notify("Invocado revocation_hook para rotación de sesiones")
        except Exception as e:
            print("Revocation hook failed:", e)

def monitor_loop():
    print("Monitor daemon started. Polling:", CONFIG["poll_interval"], "s")
    while True:
        try:
            snapshot = {}
            for k, path in CONFIG["watch_endpoints"].items():
                snapshot[k] = call_endpoint(path)
            # Analysis
            result = basic_anomaly_checks(snapshot)
            if result["alerts"]:
                print("[ALERTS]", result["alerts"])
                forensic = save_forensic_snapshot("incident", snapshot)
                notified = notify("Alerta detectada: " + "; ".join(result["alerts"]), {"forensic": forensic})
                # safe actions (rotate sessions via hook)
                take_safe_actions(snapshot)
                # request human approval for strong actions
                approved = request_containment_approval(forensic)
                if approved:
                    # If approved by humans elsewhere, implement destructive actions here (NOT automatic)
                    notify("Aprobación recibida: ejecutar acciones de contención avanzadas")
                else:
                    notify("No hay aprobación: manteniendo acciones seguras y preservando evidencia")
            else:
                print(".", end="", flush=True)
        except Exception as e:
            print("Monitor error:", e)
        time.sleep(CONFIG["poll_interval"])

if __name__ == "__main__":
    monitor_loop()
