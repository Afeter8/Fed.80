#!/usr/bin/env python3
from flask import Flask, send_file, abort
import os, subprocess, pathlib
BASE = pathlib.Path(__file__).parent.parent.resolve()
ROT_KEY = os.environ.get("ROT_KEY")
if not ROT_KEY:
    raise SystemExit("ROT_KEY required")
app = Flask(__name__)

@app.route("/file/<path:fname>")
def get_file(fname):
    # run unrotate to ensure out exists
    subprocess.run(["/usr/bin/env","python3", str(BASE/"rotate"/"unrotate.py")])
    outp = BASE / "unrotated_out" / fname
    if not outp.exists():
        abort(404)
    return send_file(str(outp))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
