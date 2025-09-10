#!/usr/bin/env python3
import os, time, json, hmac, hashlib
from pathlib import Path
BASE = Path(__file__).parent.parent.resolve()
MANIFEST = BASE / "rotated" / "manifest.json"
ROT_KEY = os.environ.get("ROT_KEY")
BACKUP = BASE / "backup"

def verify_manifest():
    if not MANIFEST.exists(): return False, "no manifest"
    m = json.loads(MANIFEST.read_text())
    h = m.pop("hmac", None)
    b = json.dumps(m, sort_keys=True).encode('utf-8')
    calc = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    m["hmac"] = h
    return calc == h, "ok" if calc == h else "hmac mismatch"

if __name__ == "__main__":
    if not ROT_KEY:
        raise SystemExit("ROT_KEY required")
    while True:
        ok, msg = verify_manifest()
        print("[verify]", ok, msg)
        if not ok:
            print("[verify] manifest corrupto -> intentar restaurar desde backup")
            # Basic restore: find last backup with rotated content (implementation depende)
        time.sleep(20)
