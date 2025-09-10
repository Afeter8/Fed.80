#!/usr/bin/env python3
# rotate_service.py
"""
Rotador reversible de archivos de texto (HTML, CSS, JS, JSON, PY...)
Genera rotated/ + manifest.json (sha512 por archivo + hmac)
Push a branch rot-<ts>-<rand> si el repo está inicializado.
"""

import os, time, json, hmac, hashlib, random, string, shutil, subprocess
from pathlib import Path

BASE = Path(__file__).parent.resolve()
SOURCE = BASE / "source"
ROTATED = BASE / "rotated"
BACKUP = BASE / "backup"
MANIFEST = ROTATED / "manifest.json"

ROT_KEY = os.environ.get("ROT_KEY")
GIT_REMOTE = os.environ.get("GIT_REMOTE", "origin")
GIT_REPO_DIR = BASE
BRANCH_PREFIX = "rot-"
ROT_INTERVAL = int(os.environ.get("ROT_INTERVAL", 600))  # default 10 min

if not ROT_KEY:
    raise SystemExit("Define ROT_KEY en el entorno (export ROT_KEY=...)")

# --- charset: letras, dígitos, puntuación, espacios, newline, tabs, y una lista básica de emojis ---
BASE_CHARS = list((string.ascii_letters + string.digits + string.punctuation + " \n\t"))
# lista básica de emojis (puedes ampliar)
EMOJIS = ["😀","😁","😂","😃","😄","😅","😆","😉","😊","😇","🙂","🙃","😍","😘","😜","🤖","🔥","✨","🌐","🔒"]
# combinamos en una lista ordenada (sin duplicados)
CHARSET = []
for c in BASE_CHARS + EMOJIS:
    if c not in CHARSET:
        CHARSET.append(c)

def rand_suffix(n=6):
    return ''.join(random.choice(string.ascii_lowercase+string.digits) for _ in range(n))

def build_map(seed: str):
    rnd = random.Random(seed)
    perm = CHARSET.copy()
    rnd.shuffle(perm)
    return {CHARSET[i]: perm[i] for i in range(len(CHARSET))}

def invert_map(mapping):
    return {v:k for k,v in mapping.items()}

def is_text_file(p: Path) -> bool:
    try:
        p.read_text(encoding='utf-8')
        return True
    except Exception:
        return False

def rotate_text(text: str, mapping: dict) -> str:
    return ''.join(mapping.get(ch, ch) for ch in text)

def sha512_file(path: Path) -> str:
    h = hashlib.sha512()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def hmac_sign(obj: bytes) -> str:
    return hmac.new(ROT_KEY.encode('utf-8'), obj, hashlib.sha512).hexdigest()

def ensure_dirs():
    SOURCE.mkdir(parents=True, exist_ok=True)
    ROTATED.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)

def snapshot_backup():
    ts = int(time.time())
    dst = BACKUP / f"backup_{ts}"
    if not dst.exists():
        shutil.copytree(SOURCE, dst)

def git_push_rotated(branch_name: str, message: str):
    try:
        subprocess.run(["git","checkout","-b",branch_name], cwd=str(GIT_REPO_DIR), check=True)
        subprocess.run(["git","add", str(ROTATED)], cwd=str(GIT_REPO_DIR), check=True)
        subprocess.run(["git","commit","-m",message], cwd=str(GIT_REPO_DIR), check=True)
        subprocess.run(["git","push","-u", GIT_REMOTE, branch_name], cwd=str(GIT_REPO_DIR), check=True)
        # volver a main/master
        try:
            subprocess.run(["git","checkout","main"], cwd=str(GIT_REPO_DIR), check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git","checkout","master"], cwd=str(GIT_REPO_DIR), check=True)
    except subprocess.CalledProcessError as e:
        print("Warning: git push failed:", e)

def rotate_cycle():
    ensure_dirs()
    snapshot_backup()
    seed = str(int(time.time())) + rand_suffix(8)
    mapping = build_map(seed)
    entries = {}
    for root,_,files in os.walk(SOURCE):
        for fname in files:
            in_path = Path(root) / fname
            rel = in_path.relative_to(SOURCE)
            out_path = ROTATED / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            # texto -> rotar; binario -> copiar tal cual
            if is_text_file(in_path):
                text = in_path.read_text(encoding='utf-8', errors='ignore')
                rotated = rotate_text(text, mapping)
                out_path.write_text(rotated, encoding='utf-8')
            else:
                shutil.copy2(in_path, out_path)
            entries[str(rel)] = {"rotated": str(out_path.relative_to(BASE)), "sha512": sha512_file(out_path)}
    manifest = {"timestamp": int(time.time()), "seed": seed, "entries": entries}
    b = json.dumps(manifest, sort_keys=True).encode('utf-8')
    manifest_hmac = hmac_sign(b)
    manifest["hmac"] = manifest_hmac
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    branch = BRANCH_PREFIX + str(int(time.time())) + "-" + rand_suffix(6)
    git_push_rotated(branch, f"Auto-rotated artifacts {manifest['timestamp']}")
    print("rotate: creada rama", branch, "manifest.hmac", manifest_hmac)
    return manifest

if __name__ == "__main__":
    print("Rotate service iniciado. ROT_INTERVAL:", ROT_INTERVAL)
    while True:
        try:
            rotate_cycle()
        except Exception as e:
            print("rotate error:", e)
        time.sleep(ROT_INTERVAL)
