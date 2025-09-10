#!/usr/bin/env python3
"""
rotate_service.py
- Rotación determinista y reversible de archivos de texto en SOURCE/
- Modos: left, right, up, down, binary (bitwise rotate)
- Crea rotated/, manifest.json con sha512 por archivo + hmac
- Hace push a rama rotativa en GitHub/GitLab si config (opcional)
- Corre en bucle eterno
"""
import os, sys, time, json, hmac, hashlib, random, string, shutil, subprocess
from pathlib import Path

BASE = Path(__file__).parent.parent.resolve()
SOURCE = BASE / "source"
ROTATED = BASE / "rotated"
BACKUP = BASE / "backup"
MANIFEST = ROTATED / "manifest.json"

ROT_KEY = os.environ.get("ROT_KEY")               # clave secreta (guardar en Vault)
GIT_REMOTE = os.environ.get("GIT_REMOTE","origin")
GIT_PUSH = os.environ.get("GIT_PUSH","false").lower() in ("1","true","yes")
BRANCH_PREFIX = "rot-"
ROT_INTERVAL = int(os.environ.get("ROT_INTERVAL", 600))
DEFAULT_MODE = os.environ.get("ROT_MODE","right")  # left/right/up/down/binary

# Charset: ASCII printable + newline + tab + emojis base
BASE_CHARS = list((string.ascii_letters + string.digits + string.punctuation + " \n\t"))
EMOJIS = ["😀","😁","😂","😃","😄","😅","😆","😉","😊","🤖","🔥","✨","🌐","🔒"]
CHARSET = []
for c in BASE_CHARS + EMOJIS:
    if c not in CHARSET:
        CHARSET.append(c)

if not ROT_KEY:
    print("ERROR: define ROT_KEY en entorno", file=sys.stderr)
    sys.exit(2)

def rand_suffix(n=6):
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def sha512_file(path: Path):
    h = hashlib.sha512()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def hmac_sign_bytes(b: bytes):
    return hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()

# ---------- ROTATION ALGORITHMS ----------
# 1) Character cyclic shift (left/right by n)
def char_shift(text: str, n: int):
    # rotate characters in CHARSET mapping, leave other chars unchanged
    mapping = {}
    L = len(CHARSET)
    for i, c in enumerate(CHARSET):
        mapping[c] = CHARSET[(i + n) % L]
    return ''.join(mapping.get(ch, ch) for ch in text)

# 2) Line rotation (up/down): rotate lines of a file
def line_rotate(text: str, lines_up: int):
    lines = text.splitlines(True)  # preserve newline chars
    if not lines:
        return text
    n = lines_up % len(lines)
    return ''.join(lines[n:] + lines[:n])

# 3) Matrix rotate (90 degrees) — useful for "up/down" visual transforms (optional)
def matrix_rotate_90(text: str, clockwise=True):
    lines = [list(line.rstrip('\n')) for line in text.splitlines()]
    if not lines: return text
    maxw = max(len(r) for r in lines)
    for r in lines:
        while len(r) < maxw:
            r.append(' ')
    if clockwise:
        rotated = list(zip(*lines[::-1]))
    else:
        rotated = list(zip(*lines))[::-1]
    return '\n'.join(''.join(row).rstrip() for row in rotated) + '\n'

# 4) Binary bitwise rotation for bytes
def bytes_rotl(b: bytes, k: int):
    out = bytearray()
    k = k % 8
    for byte in b:
        out.append(((byte << k) & 0xFF) | (byte >> (8 - k)))
    return bytes(out)

def bytes_rotr(b: bytes, k: int):
    out = bytearray()
    k = k % 8
    for byte in b:
        out.append((byte >> k) | ((byte << (8 - k)) & 0xFF))
    return bytes(out)

# ---------- helpers ----------
def is_text_file(path: Path):
    try:
        path.read_text(encoding='utf-8')
        return True
    except Exception:
        return False

def git_push_rotated(branch_name: str, message: str):
    try:
        subprocess.run(["git","checkout","-b",branch_name], cwd=str(BASE), check=True)
        subprocess.run(["git","add", str(ROTATED)], cwd=str(BASE), check=True)
        subprocess.run(["git","commit","-m",message], cwd=str(BASE), check=True)
        subprocess.run(["git","push","-u", GIT_REMOTE, branch_name], cwd=str(BASE), check=True)
        # return to main safely
        try:
            subprocess.run(["git","checkout","main"], cwd=str(BASE), check=True)
        except subprocess.CalledProcessError:
            subprocess.run(["git","checkout","master"], cwd=str(BASE), check=True)
    except subprocess.CalledProcessError as e:
        print("Warning: git push failed:", e)

def ensure_dirs():
    SOURCE.mkdir(parents=True, exist_ok=True)
    ROTATED.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)

def snapshot_backup():
    ts = int(time.time()); dst = BACKUP / f"backup_{ts}"
    if not dst.exists():
        shutil.copytree(SOURCE, dst)

# ---------- Core rotation cycle ----------
def rotate_file(in_path: Path, out_path: Path, mode: str, param: int = 1):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if is_text_file(in_path):
        text = in_path.read_text(encoding='utf-8', errors='ignore')
        if mode == "right":
            rotated = char_shift(text, param)
        elif mode == "left":
            rotated = char_shift(text, -param)
        elif mode == "up":
            rotated = line_rotate(text, param)
        elif mode == "down":
            rotated = line_rotate(text, -param)
        elif mode == "matrix_cw":
            rotated = matrix_rotate_90(text, clockwise=True)
        elif mode == "matrix_ccw":
            rotated = matrix_rotate_90(text, clockwise=False)
        else:
            rotated = text
        out_path.write_text(rotated, encoding='utf-8')
    else:
        # binary: we use bit rotation
        b = in_path.read_bytes()
        if mode == "binary_left":
            out_path.write_bytes(bytes_rotl(b, param))
        elif mode == "binary_right":
            out_path.write_bytes(bytes_rotr(b, param))
        else:
            shutil.copy2(in_path, out_path)

def rotate_cycle(mode: str = DEFAULT_MODE, param: int = 1):
    ensure_dirs()
    snapshot_backup()
    entries = {}
    seed = str(int(time.time())) + "-" + rand_suffix(8)
    # We include mode and param in manifest so unrotate knows what to do.
    for root, _, files in os.walk(SOURCE):
        for fname in files:
            in_path = Path(root) / fname
            rel = in_path.relative_to(SOURCE)
            out_path = ROTATED / rel
            rotate_file(in_path, out_path, mode, param)
            entries[str(rel)] = {"rotated": str(out_path.relative_to(BASE)), "sha512": sha512_file(out_path)}
    manifest = {"timestamp": int(time.time()), "seed": seed, "mode": mode, "param": param, "entries": entries}
    b = json.dumps(manifest, sort_keys=True).encode('utf-8')
    manifest_hmac = hmac_sign_bytes(b)
    manifest["hmac"] = manifest_hmac
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if GIT_PUSH:
        branch = BRANCH_PREFIX + str(int(time.time())) + "-" + rand_suffix(6)
        git_push_rotated(branch, f"Auto-rotated {manifest['timestamp']} mode={mode}")
        print("[rotate] pushed branch", branch)
    print("[rotate] completed mode", mode, "param", param, "hmac", manifest_hmac)
    return manifest

# ---------- main loop ----------
if __name__ == "__main__":
    print("[rotate] service starting. ROT_INTERVAL:", ROT_INTERVAL, "DEFAULT_MODE:", DEFAULT_MODE)
    while True:
        try:
            # you may choose parameterization dynamically or per file
            rotate_cycle(mode=DEFAULT_MODE, param=1)
        except Exception as e:
            print("[rotate] error:", e)
        time.sleep(ROT_INTERVAL)
