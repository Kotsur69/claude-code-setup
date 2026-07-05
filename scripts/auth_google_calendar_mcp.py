"""
Authorize Google Calendar MCP for Claude Code.
Bypasses Claude Code's DCR bug by getting tokens directly
and injecting them into .credentials.json.

Run once: python auth_google_calendar_mcp.py
"""
import json
import os
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, urlencode
import urllib.request

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(
    _SCRIPT_DIR, "client_secret_2_93926080486-9isn8ejmtt6p7a96ihs1tt6du5u2offl.apps.googleusercontent.com.json"
)
CLAUDE_CREDENTIALS = os.path.expanduser("~/.claude/.credentials.json")
CLAUDE_JSON = os.path.expanduser("~/.claude.json")

CALLBACK_PORT = 8085
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

# Google Calendar MCP scope
SCOPE = "https://www.googleapis.com/auth/calendar"

SERVER_KEY = "google-calendar|5cc3ae4d874c4870"
SERVER_NAME = "google-calendar"
SERVER_URL = "https://calendarmcp.googleapis.com/mcp/v1"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            if "code" in params:
                auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Auth OK!</h1><p>Mozesz zamknac ta karte.</p></body></html>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Blad autoryzacji</h1></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # silence server logs


def get_client_info():
    with open(CREDENTIALS_FILE, encoding="utf-8") as f:
        cred = json.load(f)
    info = cred.get("installed", cred.get("web", {}))
    return info["client_id"], info["client_secret"]


def build_auth_url(client_id):
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": "calendar_mcp",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def exchange_code(client_id, client_secret, code):
    data = urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def inject_token(token_data, client_id):
    with open(CLAUDE_CREDENTIALS, encoding="utf-8") as f:
        creds = json.load(f)

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    expires_at = int(time.time() * 1000) + expires_in * 1000

    if "mcpOAuth" not in creds:
        creds["mcpOAuth"] = {}

    creds["mcpOAuth"][SERVER_KEY] = {
        "serverName": SERVER_NAME,
        "serverUrl": SERVER_URL,
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "expiresAt": expires_at,
        "tokenType": "Bearer",
        "scope": SCOPE,
        "discoveryState": {
            "authorizationServerUrl": "https://accounts.google.com/",
            "oauthMetadataFound": True,
        },
    }

    if "mcpOAuthClientConfig" not in creds:
        creds["mcpOAuthClientConfig"] = {}

    creds["mcpOAuthClientConfig"][SERVER_KEY] = {
        "clientSecret": token_data.get("_client_secret", ""),
    }

    with open(CLAUDE_CREDENTIALS, "w", encoding="utf-8") as f:
        json.dump(creds, f, ensure_ascii=False, indent=2)

    print("[OK] Token wstrzykniety do .credentials.json")


def main():
    client_id, client_secret = get_client_info()
    print(f"Client ID: {client_id[:20]}...")

    auth_url = build_auth_url(client_id)
    print(f"\nOtwieranie przegladarki na Google consent...")
    print(f"Jesli przegladarka nie otworzy sie automatycznie, skopiuj URL:")
    print(auth_url[:80] + "...\n")

    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    server.timeout = 1
    webbrowser.open(auth_url)

    print(f"Czekam na callback na porcie {CALLBACK_PORT}...")
    deadline = time.time() + 120
    while not auth_code and time.time() < deadline:
        server.handle_request()

    server.server_close()

    if not auth_code:
        print("[BLAD] Timeout — nie otrzymano kodu autoryzacyjnego")
        return

    print("[OK] Otrzymano authorization code, wymieniam na tokeny...")
    token_data = exchange_code(client_id, client_secret, auth_code)
    token_data["_client_secret"] = client_secret

    if "access_token" not in token_data:
        print("[BLAD] Nie udalo sie uzyskac access token:", token_data)
        return

    print("[OK] Token uzyskany, zapisuje do credentials.json...")
    inject_token(token_data, client_id)

    print("\n=== GOTOWE ===")
    print("Uruchom ponownie Claude Code (lub odczekaj chwile) i sprawdz /mcp")
    print("google-calendar powinien miec status Connected")


if __name__ == "__main__":
    main()
