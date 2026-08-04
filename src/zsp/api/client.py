"""HTTP transport for the Zoho Sprints API.

Every request in the package goes through :class:`SprintsClient`, so
authentication, error handling and the ``--dry-run`` guarantee each exist
in exactly one place.

Zoho takes **query parameters** on writes, never a JSON body.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

from ..core.errors import ApiError
from .multipart import MultipartBody
from .parsing import Response


class SprintsClient:
    """Talks to ``https://sprintsapi.zoho.<dc>/zsapi``."""

    BASE = "https://sprintsapi.zoho.{dc}/zsapi"

    #: Zoho caps the data API at 30 requests/minute per token.
    RATE_LIMIT_PER_MIN = 30

    #: Safety net so a runaway ``next`` flag cannot loop forever.
    MAX_PAGES = 20

    PAGE_SIZE = 100

    def __init__(self, config, authenticator, opener=None, printer=print):
        self.config = config
        self.authenticator = authenticator
        self._opener = opener or urllib.request.urlopen
        self._print = printer

    # -- url -------------------------------------------------------------

    def build_url(self, path, params=None):
        url = self.BASE.format(dc=self.config.dc) + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        return url

    # -- verbs -----------------------------------------------------------

    def get(self, path, **params):
        """GET an endpoint and return the decoded payload."""
        return self._send(self.build_url(path, params), "GET")

    def post(self, path, dry_run=False, **params):
        """POST an endpoint, or print the request when ``dry_run``."""
        return self._write(path, "POST", dry_run, params)

    def delete(self, path, dry_run=False, **params):
        """DELETE an endpoint, or print the request when ``dry_run``."""
        return self._write(path, "DELETE", dry_run, params)

    def upload(self, path, attachments, dry_run=False, **params):
        """POST files as ``multipart/form-data``.

        The only endpoint that takes a real body — everything else is query
        parameters. Files are read and validated before the request is
        built, so a bad path fails without a partial upload.
        """
        url = self.build_url(path, params)
        if dry_run:
            self._describe("POST", url, params)
            for attachment in attachments:
                self._print(f"    file = {attachment.path} ({attachment.content_type})")
            return None

        body = MultipartBody()
        return self._send(url, "POST", body=body.encode(params, attachments),
                          content_type=body.content_type)

    def _write(self, path, method, dry_run, params):
        url = self.build_url(path, params)
        if dry_run:
            self._describe(method, url, params)
            return None
        return self._send(url, method, body=b"" if method == "POST" else None)

    def _describe(self, method, url, params):
        """Show what *would* be sent. Returns before any network access —
        this is the guardrail protecting live project data."""
        self._print("DRY RUN — would send:")
        self._print(f"  {method} {url}")
        for key, value in params.items():
            self._print(f"    {key} = {value}")

    def _send(self, url, method, body=None, content_type=None):
        token = self.authenticator.access_token(self.config)
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib.request.Request(
            url, data=body, method=method, headers=headers)
        try:
            with self._opener(request) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, exc.read().decode(), url) from exc

    # -- pagination ------------------------------------------------------

    def paginate(self, path, rows_key, page_size=None, max_pages=None, **params):
        """Follow Zoho's pagination and merge every page into one response.

        Two traps this handles, both hit in real use:

        * Pagination is by **record offset** (``index += page_size``), not
          page number — treating it as a page number silently refetches
          page one.
        * An empty trailing page omits the ``*_prop`` schema map entirely,
          so metadata always comes from the **first** page. Reading it from
          the last page turns every parsed field into ``None``.
        """
        page_size = page_size or self.PAGE_SIZE
        max_pages = max_pages or self.MAX_PAGES

        merged_rows, merged_names, first = {}, {}, None
        index = 1

        for _ in range(max_pages):
            page = self.get(path, index=index, range=page_size, **params)
            if first is None:
                first = page
            merged_rows.update(page.get(rows_key) or {})
            merged_names.update(page.get("userDisplayName") or {})
            if not (page.get("next") or page.get("hasNext")):
                break
            index += page_size

        payload = dict(first or {})
        payload[rows_key] = merged_rows
        payload["userDisplayName"] = merged_names
        return Response(payload)

    def fetch(self, path, **params):
        """GET wrapped in a :class:`~zsp.parsing.Response`."""
        return Response(self.get(path, **params))
