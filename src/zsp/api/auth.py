"""OAuth 2.0 against Zoho Accounts.

Zoho rate-limits the ``refresh_token`` grant far more aggressively than the
data API. Refreshing on every process start trips it within a handful of
commands, so :class:`Authenticator` caches the access token to disk and
renews it only once expired.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from ..core.config import Config
from ..core.errors import AuthError


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Single-shot HTTP handler that captures ``?code=`` from the redirect."""

    code = None

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        query = urllib.parse.urlparse(self.path).query
        type(self).code = urllib.parse.parse_qs(query).get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Login complete. You can close this tab.</body></html>")

    def log_message(self, *args):
        """Silence the default stderr access log."""


class Authenticator:
    """Runs the browser login flow and supplies access tokens."""

    REDIRECT_URI = "http://localhost:8723/callback"
    CALLBACK_PORT = 8723

    #: Read + write scopes. Comments need no scope of their own — they ride
    #: on ``items.*``. ``ZohoSprints.notes.*`` does not exist and is
    #: rejected at the consent screen.
    SCOPES = (
        "ZohoSprints.teams.READ,"
        "ZohoSprints.projects.READ,"
        "ZohoSprints.sprints.READ,"
        "ZohoSprints.items.READ,ZohoSprints.items.CREATE,"
        "ZohoSprints.items.UPDATE,ZohoSprints.items.DELETE,"
        "ZohoSprints.timesheets.READ,ZohoSprints.timesheets.CREATE,"
        "ZohoSprints.timesheets.DELETE,"
        "ZohoSprints.teamusers.READ,ZohoSprints.projectusers.READ"
    )

    #: Seconds of headroom before expiry at which a token is renewed.
    REFRESH_MARGIN = 60

    def __init__(self, store, opener=None):
        self.store = store
        self._opener = opener or urllib.request.urlopen

    # -- token endpoint --------------------------------------------------

    def _token_request(self, dc, payload):
        url = f"https://accounts.zoho.{dc}/oauth/v2/token"
        request = urllib.request.Request(
            url, data=urllib.parse.urlencode(payload).encode(), method="POST")
        try:
            with self._opener(request) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise AuthError(f"Token request failed: {exc.read().decode()[:300]}") from exc

    def authorize_url(self, client_id, dc):
        """The consent-screen URL the browser is sent to."""
        params = {
            "scope": self.SCOPES,
            "client_id": client_id,
            "response_type": "code",
            "access_type": "offline",
            "redirect_uri": self.REDIRECT_URI,
            "prompt": "consent",
        }
        return f"https://accounts.zoho.{dc}/oauth/v2/auth?" + urllib.parse.urlencode(params)

    # -- flows -----------------------------------------------------------

    def login(self, client_id, client_secret, dc, open_browser=True):
        """Run the browser flow and persist the resulting refresh token."""
        url = self.authorize_url(client_id, dc)
        print(f"Opening browser for login...\n{url}")
        if open_browser:
            webbrowser.open(url)

        code = self._await_callback()
        tokens = self._token_request(dc, {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": self.REDIRECT_URI,
            "code": code,
        })
        if "refresh_token" not in tokens:
            raise AuthError(f"Login failed: {tokens}")

        config = Config(client_id=client_id, client_secret=client_secret,
                        refresh_token=tokens["refresh_token"], dc=dc)
        return self.store.save(config)

    def _await_callback(self):
        OAuthCallbackHandler.code = None
        server = HTTPServer(("localhost", self.CALLBACK_PORT), OAuthCallbackHandler)
        server.handle_request()
        if not OAuthCallbackHandler.code:
            raise AuthError("No auth code received from the callback.")
        return OAuthCallbackHandler.code

    def access_token(self, config):
        """A valid access token, refreshed and cached only when stale."""
        now = time.time()
        if config.access_token and config.access_token_expiry > now + self.REFRESH_MARGIN:
            return config.access_token

        tokens = self._token_request(config.dc, {
            "grant_type": "refresh_token",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "refresh_token": config.refresh_token,
        })
        if "access_token" not in tokens:
            raise AuthError(f"Session expired or revoked. Run: zsp login  ({tokens})")

        config.access_token = tokens["access_token"]
        config.access_token_expiry = now + tokens.get("expires_in", 3600)
        self.store.save(config)
        return config.access_token
