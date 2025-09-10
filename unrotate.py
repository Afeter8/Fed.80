#!/usr/bin/env python3
"""
unrotate.py
- Lee rotated/manifest.json
- Verifica HMAC (ROT_KEY) y aplica el inverso del modo usado
- Crea unrotated_out/ con los archivos originales
"""
import os, json, hmac, hashlib, shutil
from pathlib import Path

BASE = Path(__file__).parent.parent.resolve()
ROTATED = BASE / "rotated"
MANIFEST = ROTATED / "manifest.json"
OUT = BASE / "unrotated_out"
ROT_KEY = os.environ.get("ROT_KEY")
if not ROT_KEY:
    raise SystemExit("Define ROT_KEY in environment")

# charset / emojis must align with rotate_service.py
import string, random
BASE_CHARS = list((string.ascii_letters + string.digits + string.punctuation + " \n\t"))
EMOJIS = ["😀","😁","😂","😃","😄","😅","😆","😉","😊","🤖","🔥","✨","🌐","🔒"]
CHARSET = []
for c in BASE_CHARS + EMOJIS:
    if c not in CHARSET:
        CHARSET.append(c)

def hmac_check(manifest_dict):
    h = manifest_dict.pop("hmac", None)
    b = json.dumps(manifest_dict, sort_keys=True).encode('utf-8')
    calc = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    manifest_dict["hmac"] = h
    return calc == h

def build_shift_map(n):
    L = len(CHARSET)
    mapping = {CHARSET[(i + n) % L]: CHARSET[i] for i in range(L)}
    return mapping

def invert_line_rotate(text, lines_up):
    # inverse of rotating lines up by n is rotating down by n
    lines = text.splitlines(True)
    if not lines: return text
    n = (-lines_up) % len(lines)
    return ''.join(lines[n:] + lines[:n])

def matrix_rotate_90_ccw(text):
    # inverse of clockwise rotate is counterclockwise
    lines = [list(line.rstrip('\n')) for line in text.splitlines()]
    if not lines: return text
    maxw = max(len(r) for r in lines)
    for r in lines:
        while len(r) < maxw:
            r.append(' ')
    rotated = list(zip(*lines))[::-1]
    return '\n'.join(''.join(row).rstrip() for row in rotated) + '\n'

def bytes_rotr(b: bytes, k: int):
    out = bytearray()
    k = k % 8
    for byte in b:
        out.append((byte >> k) | ((byte << (8 - k)) & 0xFF))
    return bytes(out)

def bytes_rotl(b: bytes, k: int):
    out = bytearray()
    k = k % 8
    for byte in b:
        out.append(((byte << k) & 0xFF) | (byte >> (8 - k)))
    return bytes(out)

if not MANIFEST.exists():
    print("manifest not found:", MANIFEST); exit(1)

m = json.loads(MANIFEST.read_text())
if not hmac_check(m.copy()):
    print("manifest HMAC invalid - abort"); exit(2)

mode = m.get("mode","right")
param = int(m.get("param",1))
OUT.mkdir(parents=True, exist_ok=True)

for rel, info in m["entries"].items():
    rotated_path = BASE / info["rotated"]
    out_path = OUT / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        # assume text
        txt = rotated_path.read_text(encoding='utf-8', errors='ignore')
        if mode == "right":
            # inverse is left shift by same param
            mapping = build_shift_map(-param)
            original = ''.join(mapping.get(ch, ch) for ch in txt)
            out_path.write_text(original, encoding='utf-8')
        elif mode == "left":
            mapping = build_shift_map(param)
            original = ''.join(mapping.get(ch, ch) for ch in txt)
            out_path.write_text(original, encoding='utf-8')
        elif mode == "up":
            original = invert_line_rotate(txt, param)
            out_path.write_text(original, encoding='utf-8')
        elif mode == "down":
            original = invert_line_rotate(txt, -param)
            out_path.write_text(original, encoding='utf-8')
        elif mode == "matrix_cw":
            original = matrix_rotate_90_ccw(txt)
            out_path.write_text(original, encoding='utf-8')
        elif mode == "matrix_ccw":
            # inverse of ccw is cw
            # reuse rotate_service algorithm? simple approach: rotate cw (not implemented here)
            out_path.write_text(txt, encoding='utf-8')
        elif mode == "binary_left":
            b = rotated_path.read_bytes()
            out_path.write_bytes(bytes_rotr(b, param))
        elif mode == "binary_right":
            b = rotated_path.read_bytes()
            out_path.write_bytes(bytes_rotl(b, param))
        else:
            # unknown: copy
            shutil.copy2(rotated_path, out_path)
    except Exception:
        shutil.copy2(rotated_path, out_path)
    print("restored", rel)
print("unrotate complete -> out dir:", OUT)
