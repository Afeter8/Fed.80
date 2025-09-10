#!/usr/bin/env python3
# unrotate.py
"""
Desrotador que:
- lee rotated/manifest.json
- verifica HMAC (usando ROT_KEY)
- reconstruye archivos originales (un-rotados) en out/ o en memoria
"""

import os, json, hmac, hashlib
from pathlib import Path

BASE = Path(__file__).parent.resolve()
ROTATED = BASE / "rotated"
OUT = BASE / "unrotated_out"
MANIFEST = ROTATED / "manifest.json"

ROT_KEY = os.environ.get("ROT_KEY")
if not ROT_KEY:
    raise SystemExit("Define ROT_KEY")

def hmac_check(manifest_dict):
    h = manifest_dict.pop("hmac", None)
    b = json.dumps(manifest_dict, sort_keys=True).encode('utf-8')
    calc = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    manifest_dict["hmac"] = h
    return calc == h

# same CHARSET & build_map as rotate_service - must match
import string, random
BASE_CHARS = list((string.ascii_letters + string.digits + string.punctuation + " \n\t"))
EMOJIS = ["😀","😁","😂","😃","😄","😅","😆","😉","😊","😇","🙂","🙃","😍","😘","😜","🤖","🔥","✨","🌐","🔒"]
CHARSET = []
for c in BASE_CHARS + EMOJIS:
    if c not in CHARSET:
        CHARSET.append(c)

def build_map(seed: str):
    rnd = random.Random(seed)
    perm = CHARSET.copy()
    rnd.shuffle(perm)
    return {CHARSET[i]: perm[i] for i in range(len(CHARSET))}

def invert_map(mapping):
    return {v:k for k,v in mapping.items()}

def unrotate_text(rotated: str, inv_map: dict) -> str:
    return ''.join(inv_map.get(ch, ch) for ch in rotated)

def main():
    if not MANIFEST.exists():
        print("Manifest no encontrado:", MANIFEST)
        return
    manifest = json.loads(MANIFEST.read_text())
    if not hmac_check(manifest.copy()):
        print("HMAC manifest invalido - abortando")
        return
    seed = manifest.get("seed")
    mapping = build_map(seed)
    inv = invert_map(mapping)
    OUT.mkdir(parents=True, exist_ok=True)
    for rel, info in manifest["entries"].items():
        rotated_path = BASE / info["rotated"]
        out_path = OUT / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            txt = rotated_path.read_text(encoding='utf-8', errors='ignore')
            original = unrotate_text(txt, inv)
            out_path.write_text(original, encoding='utf-8')
            print("Restored", rel)
        except Exception:
            # binario -> copiar directamente
            import shutil
            shutil.copy2(rotated_path, out_path)
            print("Copied binary", rel)

if __name__ == "__main__":
    main()
