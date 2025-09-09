# server_webauthn.py (esqueleto)
from flask import Flask, request, jsonify, session
from fido2.server import Fido2Server
from fido2 import cbor
from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
from fido2.ctap2 import AttestationObject
import os, base64

app = Flask(__name__)
app.secret_key = os.urandom(32)

RP = PublicKeyCredentialRpEntity(name="TigoStart", id="example.com")
server = Fido2Server(RP)

# in-memory storage for demo (use DB in prod)
USERS = {}  # username -> {id, name, displayName, credentials: [{cred}]}

def b64(u): return base64.b64encode(u).decode('utf-8')
def ub64(s): return base64.b64decode(s)

@app.route('/register/options', methods=['POST'])
def register_options():
    username = request.json.get('username')
    user = USERS.get(username)
    if not user:
        user_id = os.urandom(16)
        USERS[username] = {"id": user_id, "name": username, "displayName": username, "credentials": []}
        user = USERS[username]
    user_entity = PublicKeyCredentialUserEntity(id=user['id'], name=user['name'], display_name=user['displayName'])
    registration_data, state = server.register_begin(user_entity, user['credentials'])
    session['state'] = state
    # convert buffers to base64 for JSON transport
    reg = registration_data
    reg['publicKey']['challenge'] = b64(reg['publicKey']['challenge'])
    reg['publicKey']['user']['id'] = b64(reg['publicKey']['user']['id'])
    return jsonify(reg)

@app.route('/register/complete', methods=['POST'])
def register_complete():
    username = request.json['username']
    cred = request.json['credential']
    state = session.get('state')
    # reconstruct objects
    clientDataJSON = base64.b64decode(cred['response']['clientDataJSON'])
    attObj = base64.b64decode(cred['response']['attestationObject'])
    auth_data = server.register_complete(state, clientDataJSON, attObj)
    # store credential public key and id
    USERS[username]['credentials'].append({
        'cred_id': cred['rawId'],
        'public_key': auth_data.credential_public_key
    })
    return jsonify({"status":"ok"})

@app.route('/login/options', methods=['POST'])
def login_options():
    username = request.json.get('username')
    user = USERS.get(username)
    if not user:
        return jsonify({"error":"user not found"}), 404
    allow = []
    for c in user['credentials']:
        allow.append({"type":"public-key","id": c['cred_id']})
    auth_data, state = server.authenticate_begin(allow)
    session['auth_state'] = state
    # encode arrays to base64
    auth_data['publicKey']['challenge'] = b64(auth_data['publicKey']['challenge'])
    if 'allowCredentials' in auth_data['publicKey']:
        for c in auth_data['publicKey']['allowCredentials']:
            c['id'] = b64(c['id'])
    return jsonify(auth_data)

@app.route('/login/complete', methods=['POST'])
def login_complete():
    username = request.json['username']
    cred = request.json['credential']
    state = session.get('auth_state')
    clientDataJSON = base64.b64decode(cred['response']['clientDataJSON'])
    authnr_data = base64.b64decode(cred['response']['authenticatorData'])
    signature = base64.b64decode(cred['response']['signature'])
    # verify — lookup credential public key from USERS
    user = USERS.get(username)
    # find credential by id
    # (rawId is base64 of bytes)
    for c in user['credentials']:
        if c['cred_id'] == cred['rawId']:
            stored_cred = c
            break
    server.authenticate_complete(state, stored_cred['public_key'], cred['rawId'], clientDataJSON, authnr_data, signature)
    return jsonify({"status":"ok","message":"autenticado"})

if __name__=='__main__':
    app.run(debug=True, ssl_context='adhoc')
