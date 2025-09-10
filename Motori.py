#!/usr/bin/env python3
import time, json, hashlib, shutil
from pathlib import Path
BASE = Path("/opt/star-tigo-defensa")
MIRRORS = BASE / "mirrors"
WORK = BASE / "work"
HASH_STORE = BASE / "hash_store.json"
WATCH = [
    "/var/www/site/index.html",
    "/var/www/site/app.js"
]

def sha(b): import hashlib; h=hashlib.sha512(); h.update(b); return h.hexdigest()
def load():
    try: return json.loads(HASH_STORE.read_text())
    except: return {}
def save(d): HASH_STORE.write_text(json.dumps(d,indent=2))
def snapshot(name,content):
    ts=int(time.time()); p=WORK/f"{name}_{ts}.bin"; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(content); shutil.copy2(p,MIRRORS/p.name); return p
def verify():
    s = load()
    for f in WATCH:
        p = Path(f)
        if not p.exists():
            mirror = next(MIRRORS.glob(p.name + "*"), None)
            if mirror:
                p.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(mirror, p)
                s[f] = sha(p.read_bytes()); print("restored",f)
            else:
                print("missing and no mirror", f)
            continue
        h = sha(p.read_bytes())
        if s.get(f) != h:
            print("change detected", f)
            snapshot(Path(f).name, p.read_bytes())
            mirror = next(MIRRORS.glob(Path(f).name + "*"), None)
            if mirror:
                shutil.copy2(mirror, p)
                s[f] = sha(p.read_bytes()); print("repaired from mirror", f)
            else:
                s[f] = h
    save(s)

if __name__ == "__main__":
    while True:
        try: verify()
        except Exception as e: print("monitor err", e)
        time.sleep(15)
