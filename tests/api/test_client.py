"""SprintsClient: URLs, verbs, errors, pagination and the dry-run guard."""

import io
import urllib.error

import pytest

from zsp.api import SprintsClient
from zsp.core import ApiError

from ..conftest import OK, StubAuthenticator


class TestUrlBuilding:
    def test_uses_the_configured_data_centre(self, client):
        client.config.dc = "eu"
        assert client.build_url("/teams/") == "https://sprintsapi.zoho.eu/zsapi/teams/"

    def test_encodes_query_parameters(self, client):
        url = client.build_url("/team/1/item/", {"name": "hello world", "point": 3})
        assert url.endswith("/team/1/item/?name=hello+world&point=3")

    def test_omits_the_question_mark_without_params(self, client):
        assert client.build_url("/teams/").endswith("/teams/")


class TestVerbs:
    def test_get_issues_a_get(self, client, opener):
        opener.payloads.append(OK)
        assert client.get("/teams/") == OK
        assert opener.methods == ["GET"]

    def test_post_issues_a_post(self, client, opener):
        client.post("/team/1/item/", name="x")
        assert opener.methods == ["POST"]

    def test_delete_issues_a_delete(self, client, opener):
        client.delete("/team/1/item/9/")
        assert opener.methods == ["DELETE"]

    def test_token_is_requested_once_per_call(self, config, opener):
        auth = StubAuthenticator()
        client = SprintsClient(config, auth, opener=opener, printer=lambda *a: None)
        client.get("/teams/")
        client.get("/teams/")
        assert auth.calls == 2


class TestErrorHandling:
    def test_http_error_becomes_api_error(self, config):
        def explode(request):
            raise urllib.error.HTTPError(
                request.full_url, 401, "Unauthorized", {},
                io.BytesIO(b'{"code":7601,"message":"Invalid oauthscope"}'))

        client = SprintsClient(config, StubAuthenticator(), opener=explode)

        with pytest.raises(ApiError) as caught:
            client.get("/teams/")

        assert caught.value.status == 401
        assert caught.value.exit_code == 4
        assert "7601" in caught.value.body

    def test_api_error_keeps_the_url_for_debugging(self, config):
        def explode(request):
            raise urllib.error.HTTPError(
                request.full_url, 500, "boom", {}, io.BytesIO(b"{}"))

        client = SprintsClient(config, StubAuthenticator(), opener=explode)
        with pytest.raises(ApiError) as caught:
            client.get("/teams/")
        assert caught.value.url.endswith("/teams/")

    def test_error_message_is_truncated(self, config):
        def explode(request):
            raise urllib.error.HTTPError(
                request.full_url, 500, "boom", {}, io.BytesIO(b"x" * 5000))

        client = SprintsClient(config, StubAuthenticator(), opener=explode)
        with pytest.raises(ApiError) as caught:
            client.get("/teams/")
        assert len(str(caught.value)) < 400


class TestDryRun:
    """The guardrail: --dry-run must never reach Zoho."""

    def test_no_network_call_is_made(self, config, opener):
        printed = []
        client = SprintsClient(config, StubAuthenticator(), opener=opener,
                               printer=printed.append)

        result = client.post("/team/1/item/", dry_run=True, name="x")

        assert result is None
        assert opener.calls == [], "dry run must not perform any HTTP call"
        assert any("DRY RUN" in line for line in printed)
        assert any("name = x" in line for line in printed)

    def test_the_verb_is_shown(self, config, opener):
        printed = []
        client = SprintsClient(config, StubAuthenticator(), opener=opener,
                               printer=printed.append)
        client.delete("/team/1/item/9/", dry_run=True)
        assert any("DELETE" in line for line in printed)

    def test_no_token_is_requested(self, config, opener):
        auth = StubAuthenticator()
        client = SprintsClient(config, auth, opener=opener, printer=lambda *a: None)
        client.post("/x/", dry_run=True)
        assert auth.calls == 0


class TestPagination:
    def test_advances_by_record_offset(self, client, opener):
        opener.payloads.extend([
            {"rows": {"a": [1]}, "rows_prop": {"x": 0}, "next": True},
            {"rows": {"b": [2]}, "rows_prop": {"x": 0}, "next": False},
        ])

        merged = client.paginate("/p/", "rows", page_size=100)

        assert set(merged["rows"]) == {"a", "b"}
        assert opener.query(0)["index"] == "1"
        # Offset, not page number: the second call starts at record 101.
        assert opener.query(1)["index"] == "101"

    def test_schema_comes_from_the_first_page(self, client, opener):
        """Regression: an empty trailing page omits *_prop entirely.

        Taking metadata from the last page turned every field into None.
        """
        opener.payloads.extend([
            {"rows": {"a": ["v"]}, "rows_prop": {"x": 0}, "next": True},
            {"next": False},  # no rows, no rows_prop
        ])

        merged = client.paginate("/p/", "rows", page_size=100)

        assert merged["rows_prop"] == {"x": 0}
        assert merged.rows("rows", "rows_prop", {"x": "x"}) == [{"id": "a", "x": "v"}]

    def test_honours_the_has_next_alias(self, client, opener):
        """Timesheet responses use hasNext where items use next."""
        opener.payloads.extend([
            {"rows": {"a": [1]}, "hasNext": True},
            {"rows": {"b": [2]}, "hasNext": False},
        ])
        assert set(client.paginate("/p/", "rows")["rows"]) == {"a", "b"}

    def test_stops_at_max_pages(self, client, opener):
        opener.payloads.extend({"rows": {str(i): [i]}, "next": True} for i in range(50))
        client.paginate("/p/", "rows", max_pages=3)
        assert len(opener.calls) == 3

    def test_merges_display_names_across_pages(self, client, opener):
        opener.payloads.extend([
            {"rows": {"a": [1]}, "userDisplayName": {"1": "Ada"}, "next": True},
            {"rows": {"b": [2]}, "userDisplayName": {"2": "Grace"}, "next": False},
        ])
        merged = client.paginate("/p/", "rows")
        assert merged.display_names == {"1": "Ada", "2": "Grace"}

    def test_tolerates_an_empty_first_page(self, client, opener):
        opener.payloads.append({"next": False})
        merged = client.paginate("/p/", "rows")
        assert merged["rows"] == {}
