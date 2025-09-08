#!/usr/bin/env python3
# scanner_orchestrator.py - análisis básico: ClamAV + YARA + VirusTotal (opcional)
import os, hashlib, shutil, subprocess, json
from datetime import datetime

WATCH_DIR = "/ruta/a/entradas"
QUARANTINE_DIR = "/ruta/a/quarantine"
VIRUSTOTAL_KEY = None  # pon tu clave o deja None
YARA_RULES = "/ruta/yara/rules.yar"

def sha256(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def clamav_scan(path):
    res = subprocess.run(["clamscan", "--no-summary", path], capture_output=True, text=True)
    return res.returncode == 1 or "FOUND" in res.stdout

def yara_scan(path):
    res = subprocess.run(["yara", "-m", YARA_RULES, path], capture_output=True, text=True)
    return res.stdout.strip()

def virustotal_lookup(path):
    if not VIRUSTOTAL_KEY:
        return None
    import requests
    h = sha256(path)
    url = "https://www.virustotal.com/api/v3/files/" + h
    r = requests.get(url, headers={"x-apikey": VIRUSTOTAL_KEY})
    if r.status_code==200:
        return r.json()
    return None

def process_file(path):
    print(f"[{datetime.now().isoformat()}] Procesando {path}")
    h = sha256(path)
    findings = {}
    findings['sha256'] = h
    findings['clamav'] = clamav_scan(path)
    findings['yara'] = yara_scan(path)
    vt = virustotal_lookup(path)
    findings['virustotal'] = vt is not None
    # si hay hallazgos, mover a cuarentena
    if findings['clamav'] or findings['yara'] or findings['virustotal']:
        basename = os.path.basename(path)
        dest = os.path.join(QUARANTINE_DIR, basename + "." + h[:8])
        shutil.move(path, dest)
        findings['quarantined_to'] = dest
    # guardar evidencia
    with open(os.path.join(QUARANTINE_DIR, f"report_{h[:8]}.json"), "w") as f:
        json.dump(findings, f, indent=2, default=str)
    return findings

if __name__ == "__main__":
    os.makedirs(QUARANTINE_DIR, exist_ok=True)
    for fname in os.listdir(WATCH_DIR):
        full = os.path.join(WATCH_DIR, fname)
        if os.path.isfile(full):
            print(process_file(full))
