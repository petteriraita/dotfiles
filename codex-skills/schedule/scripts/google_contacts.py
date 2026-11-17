#!/usr/bin/env python3
"""Google Contacts CLI with persistent OAuth and create/readback verification."""
import argparse
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

CONFIG = Path.home() / '.config/phone-schedule'
TOKEN = CONFIG / 'google-contacts-token.json'
CLIENT = Path.home() / 'dev/personal/automation/calendar-llm/credentials.json'
SCOPES = 'openid email https://www.googleapis.com/auth/contacts'
BASE = 'https://people.googleapis.com/v1/'


class ApiError(RuntimeError):
    pass


def request(url, method='GET', data=None, headers=None, form=False):
    headers = dict(headers or {})
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, body, headers, method=method), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get('error', {})
            text = err.get('message', 'API request rejected') if isinstance(err, dict) else str(err)
        except (ValueError, AttributeError):
            text = 'API request rejected'
        raise ApiError(f'HTTP {e.code}: {text}') from None
    except (TimeoutError, urllib.error.URLError):
        raise ApiError('Request did not complete. For a write, outcome may be unknown; inspect contacts before retrying.') from None


def client():
    if not CLIENT.is_file():
        raise ApiError(f'OAuth client file is missing: {CLIENT}')
    data = json.loads(CLIENT.read_text()).get('installed')
    if not data:
        raise ApiError('An installed-app OAuth client is required.')
    return data


def save(token):
    CONFIG.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(CONFIG, 0o700)
    fd, path = tempfile.mkstemp(prefix='.contacts-', dir=CONFIG)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(token, f)
        os.replace(path, TOKEN)
    finally:
        if os.path.exists(path): os.unlink(path)


def access():
    if not TOKEN.is_file():
        raise ApiError('Contacts authorization is not configured. Run the auth command once.')
    token = json.loads(TOKEN.read_text())
    if token.get('expires_at', 0) < time.time() + 60:
        c = client()
        new = request(c.get('token_uri', 'https://oauth2.googleapis.com/token'), 'POST', {
            'client_id': c['client_id'], 'client_secret': c['client_secret'],
            'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'}, form=True)
        token.update(new); token['expires_at'] = time.time() + new.get('expires_in', 3600)
        save(token)
    return token['access_token']


def api(path, method='GET', data=None):
    return request(BASE + path, method, data, {'Authorization': 'Bearer ' + access()})


def identity(expected):
    info = request('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': 'Bearer ' + access()})
    if info.get('email', '').casefold() != expected.casefold() or not info.get('email_verified'):
        raise ApiError('The authorized Google identity does not match the intended account; no contact was changed.')
    return info['email']


def authorize(expected):
    c = client(); state = secrets.token_urlsafe(32); verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    result = {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if self.path.split('?')[0] != '/callback' or not secrets.compare_digest(q.get('state', [''])[0], state):
                self.send_error(400, 'Invalid OAuth callback'); return
            if 'code' in q: result['code'] = q['code'][0]
            else: result['error'] = q.get('error', ['Authorization was not completed'])[0]
            self.send_response(200); self.end_headers()
            self.wfile.write(b'Authorization received. You can close this tab and return to Codex.')
    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        server.timeout = 1
        redirect = f'http://127.0.0.1:{server.server_port}/callback'
        params = {'client_id': c['client_id'], 'redirect_uri': redirect, 'response_type': 'code',
                  'scope': SCOPES, 'access_type': 'offline', 'prompt': 'consent',
                  'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256',
                  'login_hint': expected}
        url = c.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth') + '?' + urllib.parse.urlencode(params)
        print('Authorize Google Contacts for ' + expected + ':\n' + url, flush=True)
        try:
            subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
        deadline = time.time() + 600
        while not result and time.time() < deadline:
            server.handle_request()
        if 'code' not in result: raise ApiError('Google consent was not completed: ' + result.get('error', 'timed out'))
        token = request(c.get('token_uri', 'https://oauth2.googleapis.com/token'), 'POST', {
            'client_id': c['client_id'], 'client_secret': c['client_secret'],
            'code': result['code'], 'code_verifier': verifier, 'redirect_uri': redirect,
            'grant_type': 'authorization_code'}, form=True)
    if not token.get('refresh_token'): raise ApiError('Google did not return persistent authorization; setup is incomplete.')
    if 'https://www.googleapis.com/auth/contacts' not in token.get('scope', '').split():
        raise ApiError('Google sign-in succeeded, but Contacts permission was not granted. Select the Contacts permission checkbox in the consent screen. Existing authorization was preserved.')
    # Verify the identity before replacing any stored authorization.
    info = request('https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization': 'Bearer ' + token['access_token']})
    if info.get('email', '').casefold() != expected.casefold() or not info.get('email_verified'):
        raise ApiError('Wrong Google account selected. Existing Contacts authorization was preserved.')
    token['expires_at'] = time.time() + token.get('expires_in', 3600)
    token['account_email'] = info['email']; save(token)
    api('people/me/connections?' + urllib.parse.urlencode({'personFields': 'names,phoneNumbers', 'pageSize': 1}))
    print(json.dumps({'authorized': True, 'account': info['email'], 'contacts_api_verified': True}))


def digits(value):
    return ''.join(c for c in value if c.isdigit())


def ensure_contact(args):
    email = identity(args.account)
    if not args.number.startswith('+') or not 7 <= len(digits(args.number)) <= 15:
        raise ApiError('Use a phone number with +country code.')
    page = None; matches = []
    while True:
        params = {'personFields': 'names,phoneNumbers', 'pageSize': 1000}
        if page: params['pageToken'] = page
        data = api('people/me/connections?' + urllib.parse.urlencode(params))
        matches.extend(p for p in data.get('connections', []) if any(digits(n.get('value', '')) == digits(args.number) for n in p.get('phoneNumbers', [])))
        page = data.get('nextPageToken')
        if not page: break
    created = False
    if matches:
        if len(matches) > 1: raise ApiError('Multiple existing contacts have this number; inspect before making changes.')
        person = matches[0]
    else:
        body = {'names': [{'givenName': args.name}], 'phoneNumbers': [{'value': args.number, 'type': 'work'}]}
        if args.notes: body['biographies'] = [{'value': args.notes, 'contentType': 'TEXT_PLAIN'}]
        person = api('people:createContact?personFields=names,phoneNumbers,metadata', 'POST', body)
        created = True
    resource = person['resourceName']
    verified = api(resource + '?personFields=names,phoneNumbers,metadata')
    if not any(digits(n.get('value', '')) == digits(args.number) for n in verified.get('phoneNumbers', [])):
        raise ApiError('Saved contact readback did not match the requested number; inspect before retrying.')
    if not any(n.get('displayName', '') == args.name or n.get('givenName', '') == args.name for n in verified.get('names', [])):
        raise ApiError('A contact with this phone number exists under another name. It was preserved; inspect before renaming or duplicating.')
    print(json.dumps({'created': created, 'verified': True, 'account': email,
                      'resourceName': resource, 'names': verified.get('names'),
                      'phoneNumbers': verified.get('phoneNumbers'), 'phone_sync_verified': False}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--account', default='petteri.r.raita@gmail.com')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('auth'); status = sub.add_parser('status'); status.add_argument('--refresh', action='store_true')
    c = sub.add_parser('ensure-contact'); c.add_argument('--name', required=True); c.add_argument('--number', required=True); c.add_argument('--notes', default='')
    a = p.parse_args()
    try:
        if a.command == 'auth': authorize(a.account)
        elif a.command == 'status':
            if a.refresh:
                if not TOKEN.is_file(): raise ApiError('Contacts authorization is not configured.')
                token = json.loads(TOKEN.read_text()); token['expires_at'] = 0; save(token)
            email = identity(a.account)
            api('people/me/connections?personFields=names,phoneNumbers&pageSize=1')
            print(json.dumps({'authorized': True, 'account': email, 'contacts_api_verified': True, 'refresh_tested': a.refresh}))
        else: ensure_contact(a)
    except (ApiError, ValueError, KeyError) as e:
        print(str(e), file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
