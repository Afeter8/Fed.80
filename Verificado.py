#!/usr/bin/env python3
# verify_loop.py
import os, json, time, hmac, hashlib
from pathlib import Path

BASE = Path(__file__).parent.resolve()
ROTATED = BASE / "rotated"
MANIFEST = ROTATED / "manifest.json"
ROT_KEY = os.environ.get("ROT_KEY")
BACKUP = BASE / "backup"

def verify_manifest():
    if not MANIFEST.exists():
        return False, "manifest not found"
    m = json.loads(MANIFEST.read_text())
    h = m.pop("hmac", None)
    b = json.dumps(m, sort_keys=True).encode('utf-8')
    calc = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    m["hmac"] = h
    if calc == h:
        return True, "ok"
    else:
        return False, "hmac mismatch"

if __name__ == "__main__":
    if not ROT_KEY:
        raise SystemExit("Define ROT_KEY")
    while True:
        ok, msg = verify_manifest()
        print("verify:", ok, msg)
        if not ok:
            print("Manifest corrupto -> restaurando desde backup (si aplica)")
            # logica para restore desde BACKUP (ejemplo simple: copiar último backup)
            backups = sorted(BACKUP.glob("backup_*"), reverse=True)
            if backups:
                # restaurar rotated desde backup (si backup contiene source -> re-run rotate)
                print("Found backups:", backups[0])
            else:
                print("No backups disponibles")
        time.sleep(20)
