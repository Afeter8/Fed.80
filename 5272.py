#!/usr/bin/env python3
# sign_manifest.py -- calcula/valida HMAC-SHA512 para manifest.json
import json, hmac, hashlib, sys, os
from pathlib import Path

MANIFEST = Path('manifest.json')
ROT_KEY = os.environ.get('ROT_KEY') or "CAMBIAR_POR_KEY_SEGURA"  # usar Vault/EKV en prod

def sign(manifest_path=MANIFEST):
    m = json.loads(manifest_path.read_text(encoding='utf-8'))
    if 'hmac' in m: m.pop('hmac')
    b = json.dumps(m, sort_keys=True).encode('utf-8')
    h = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    m['hmac'] = h
    manifest_path.write_text(json.dumps(m, indent=2), encoding='utf-8')
    print("Manifest firmado:", h)

def verify(manifest_path=MANIFEST):
    m = json.loads(manifest_path.read_text(encoding='utf-8'))
    h = m.get('hmac')
    if not h:
        print("No hmac")
        return False
    m.pop('hmac')
    b = json.dumps(m, sort_keys=True).encode('utf-8')
    calc = hmac.new(ROT_KEY.encode('utf-8'), b, hashlib.sha512).hexdigest()
    ok = calc == h
    print("Verificación:", ok)
    return ok

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: sign_manifest.py sign|verify")
        sys.exit(2)
    if sys.argv[1] == 'sign':
        sign()
    else:
        verify()
