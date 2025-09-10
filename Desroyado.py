#!/usr/bin/env python3
# loader_server.py
from flask import Flask, send_file, abort
import os, json, hmac, hashlib
from pathlib import Path
import tempfile
import shutil
import subprocess

BASE = Path(__file__).parent.resolve()
ROTATED = BASE / "rotated"
MANIFEST = ROTATED / "manifest.json"
ROT_KEY = os.environ.get("ROT_KEY")
UNROT_DIR = BASE / "unrot_temp"

app = Flask(__name__)

def verify_manifest_and_unrotate():
    if not MANIFEST.exists():
        return False, "no manifest"
    m = json.loads(MANIFEST.read_text())
    h = m.pop("hmac", None)
    b = json.dumps(m, sort_keys=True).encode('utf-8')
    calc = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    m["hmac"] = h
    if calc != h:
        return False, "invalid hmac"
    # si ok, llamar unrotate.py para recrear OUT en memoria / tmp
    # para simplicidad: ejecutar unrotate.py que llena unrot_temp/
    subprocess.run(["/usr/bin/env","python3", str(BASE/"unrotate.py")], check=False)
    return True, "unrotated"

@app.route("/file/<path:fname>")
def get_file(fname):
    ok, msg = verify_manifest_and_unrotate()
    if not ok:
        abort(503, f"Manifest error: {msg}")
    outf = BASE / "unrotated_out" / fname
    if not outf.exists():
        abort(404)
    return send_file(str(outf))

if __name__ == "__main__":
    if not ROT_KEY:
        raise SystemExit("Define ROT_KEY")
    app.run(host="0.0.0.0", port=8080)
