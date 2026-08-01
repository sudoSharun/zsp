"""Authenticator: token caching, refresh and the OAuth URL."""

import io
import time
import urllib.error

import pytest

from zsp.api import Authenticator
from zsp.core import AuthError, ConfigStore

from ..conftest import FakeResponse


class StubOpener:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        return FakeResponse(self.payload)


@pytest.fixture
def store(tmp_path):
    return ConfigStore(str(tmp_path))


class TestAccessToken:
    def test_cached_token_avoids_a_refresh(self, store, config):
        opener = StubOpener({})
        auth = Authenticator(store, opener=opener)

        assert auth.access_token(config) == config.access_token
        assert opener.calls == 0, "a live token must not trigger a refresh"

    def test_expired_token_is_refreshed_and_saved(self, store, config):
        config.access_token_expiry = time.time() - 1
        store.save(config)
        opener = StubOpener({"access_token": "fresh", "expires_in": 3600})

        token = Authenticator(store, opener=opener).access_token(config)

        assert token == "fresh"
        assert opener.calls == 1
        # Persisted, so the next process reuses it rather than refreshing.
        assert store.load().access_token == "fresh"

    def test_token_expiring_within_the_margin_is_refreshed(self, store, config):
        config.access_token_expiry = time.time() + 10  # inside REFRESH_MARGIN
        store.save(config)
        opener = StubOpener({"access_token": "fresh", "expires_in": 3600})

        Authenticator(store, opener=opener).access_token(config)
        assert opener.calls == 1

    def test_missing_token_in_response_raises(self, store, config):
        config.access_token = None
        opener = StubOpener({"error": "invalid_grant"})

        with pytest.raises(AuthError) as caught:
            Authenticator(store, opener=opener).access_token(config)

        assert "zsp login" in str(caught.value)
        assert caught.value.exit_code == 3

    def test_defaults_expiry_when_absent(self, store, config):
        config.access_token = None
        store.save(config)
        opener = StubOpener({"access_token": "fresh"})  # no expires_in

        auth = Authenticator(store, opener=opener)
        auth.access_token(config)
        assert config.access_token_expiry > time.time()


class TestTokenErrors:
    def test_http_failure_becomes_auth_error(self, store, config):
        def explode(request):
            raise urllib.error.HTTPError(
                "https://accounts.zoho.in/oauth/v2/token", 400, "bad", {},
                io.BytesIO(b'{"error":"invalid_client"}'))

        config.access_token = None
        with pytest.raises(AuthError) as caught:
            Authenticator(store, opener=explode).access_token(config)

        assert "Token request failed" in str(caught.value)
        assert "invalid_client" in str(caught.value)
        assert caught.value.exit_code == 3


class TestAuthorizeUrl:
    def test_contains_the_required_parameters(self, store):
        url = Authenticator(store).authorize_url("CLIENT", "in")

        assert url.startswith("https://accounts.zoho.in/oauth/v2/auth?")
        assert "client_id=CLIENT" in url
        assert "access_type=offline" in url  # required to get a refresh token
        assert "prompt=consent" in url

    def test_requests_read_and_write_scopes(self, store):
        url = Authenticator(store).authorize_url("CLIENT", "in")
        for scope in ("items.READ", "items.CREATE", "items.UPDATE",
                      "items.DELETE", "timesheets.CREATE"):
            assert scope.replace(".", "%2E") in url or scope in url.replace("%2C", ","), scope

    def test_omits_any_notes_scope(self, store):
        """ZohoSprints.notes.* does not exist; requesting it breaks login."""
        assert "notes" not in Authenticator(store).authorize_url("CLIENT", "in")

    def test_targets_the_configured_data_centre(self, store):
        assert "accounts.zoho.eu" in Authenticator(store).authorize_url("C", "eu")
