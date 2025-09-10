#!/usr/bin/env python3
"""
Create ClouDNS monitoring check via JSON API.
Requires: CLOUDNS_AUTH_ID, CLOUDNS_AUTH_PASS in env
Docs: https://www.cloudns.net/wiki/article/398/ (create monitoring check)
"""
import os, requests, json

API_BASE = "https://panel.cloudns.net/api/json/monitoring/add-monitor/"

AUTH_ID = os.environ.get("CLOUDNS_AUTH_ID")
AUTH_PASS = os.environ.get("CLOUDNS_AUTH_PASS")

if not AUTH_ID or not AUTH_PASS:
    raise SystemExit("Set CLOUDNS_AUTH_ID and CLOUDNS_AUTH_PASS in env")

def create_monitor(name, mtype, host, **kwargs):
    # common params
    params = {
        "auth-id": AUTH_ID,
        "auth-password": AUTH_PASS,
        "name": name,
        "type": mtype,   # e.g. web, ping, tcp, udp, dns, heartbeat, ssl, smtp, imap, streaming, keyword
        "host": host
    }
    # merge any extra kwargs if provided by caller (port, keyword, interval, regionNodes, ...)
    params.update(kwargs)
    r = requests.post(API_BASE, data=params, timeout=30)
    j = r.json()
    return j

if __name__ == "__main__":
    # Ejemplo: crear monitor Web cada 10 minutos para example.com
    res = create_monitor(name="fgm-web-check", mtype="web", host="example.com", period="10")
    print(json.dumps(res, indent=2, ensure_ascii=False))
