#!/usr/bin/env python3
# agent.py - minimal reporting agent (no exec arbitrary code)
import os, time, json, hashlib, requests, platform
from pathlib import Path

API_URL = os.environ.get('API_URL', 'http://localhost:8000')  # backend maestro
HOSTNAME = os.environ.get('HOSTNAME', platform.node())
WATCH_DIRS = os.environ.get('WATCH_DIRS', '/opt/star-tigo-defensa/source').split(';')
REPORT_INTERVAL = int(os.environ.get('REPORT_INTERVAL', 30))

def sha512_bytes(b):
    import hashlib
    return hashlib.sha512(b).hexdigest()

def scan_files():
    entries = {}
    for d in WATCH_DIRS:
        p = Path(d)
        if not p.exists(): continue
        for f in p.rglob('*'):
            if f.is_file():
                try:
                    b = f.read_bytes()
                    entries[str(f)] = sha512_bytes(b)
                except Exception:
                    continue
    return entries

def report():
    payload = {
        "host": HOSTNAME,
        "os": platform.platform(),
        "timestamp": int(time.time()),
        "files": scan_files()
    }
    try:
        r = requests.post(API_URL + '/api/agent/report', json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print("Reporte error:", e)
        return None

def poll_commands():
    try:
        r = requests.get(API_URL + '/api/agent/commands?host=' + HOSTNAME, timeout=8)
        if r.ok:
            return r.json().get('commands',[])
    except Exception as e:
        print("cmd poll error:", e)
    return []

def run_loop():
    while True:
        res = report()
        print("Reported:", res)
        cmds = poll_commands()
        for c in cmds:
            print("Received command:", c.get('action'))
            # Actions are only signals; agent will request repair/scan but not execute arbitrary code
            if c.get('action') == 'scan':
                _ = scan_files()
            elif c.get('action') == 'repair-request':
                # create a request job to server so human-approved retriever re-deploy from mirrors
                requests.post(API_URL + '/api/agent/repair_request', json={"host":HOSTNAME})
        time.sleep(REPORT_INTERVAL)

if __name__ == "__main__":
    run_loop()
