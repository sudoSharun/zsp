"""Write paths: endpoint shape, parameter encoding, dry-run safety."""

import json

import pytest

from zsp.core import UsageError

from ..conftest import (
    ITEM,
    ITEM_TYPES_RESPONSE,
    NOTE,
    OK,
    PRIORITIES_RESPONSE,
    PRIORITY_HIGH,
    PROJECT,
    SPRINT,
    STATUS_DONE,
    STATUS_RESPONSE,
    TYPE_BUG,
    USER,
    USERS_RESPONSE,
)


class TestCreate:
    def test_posts_to_the_item_endpoint(self, services, opener):
        services["items"].create("New item", PROJECT, SPRINT)

        assert opener.methods == ["POST"]
        assert opener.urls[-1].endswith(f"/sprints/{SPRINT}/item/?name=New+item")

    def test_parent_targets_the_subitem_path(self, services, opener):
        services["items"].create("Child", PROJECT, SPRINT, parent=ITEM)
        assert f"/item/{ITEM}/subitem/" in opener.urls[-1]

    def test_assignee_is_encoded_as_a_json_array(self, services, opener):
        opener.payloads.extend([USERS_RESPONSE, OK])
        services["items"].create("x", PROJECT, SPRINT, assignee="ada")
        assert json.loads(opener.query()["users"]) == [USER]

    def test_type_and_priority_names_are_resolved(self, services, opener):
        opener.payloads.extend([ITEM_TYPES_RESPONSE, PRIORITIES_RESPONSE, OK])
        services["items"].create("x", PROJECT, SPRINT, item_type="bug", priority="high")

        params = opener.query()
        assert params["projitemtypeid"] == TYPE_BUG
        assert params["projpriorityid"] == PRIORITY_HIGH

    def test_dates_are_normalised(self, services, opener):
        services["items"].create("x", PROJECT, SPRINT,
                                 start="2026-01-05", end="2026-01-09")

        params = opener.query()
        assert params["startdate"] == "2026-01-05T00:00:00+0000"
        assert params["enddate"] == "2026-01-09T00:00:00+0000"

    def test_points_of_zero_are_still_sent(self, services, opener):
        services["items"].create("x", PROJECT, SPRINT, points=0)
        assert opener.query()["point"] == "0"


class TestUpdate:
    def test_status_name_is_resolved(self, services, opener):
        opener.payloads.extend([STATUS_RESPONSE, OK])
        services["items"].update(ITEM, PROJECT, SPRINT, status="done")
        assert opener.query()["statusid"] == STATUS_DONE

    def test_an_empty_description_clears_the_field(self, services, opener):
        """Regression: a truthiness check dropped "" and silently no-oped."""
        services["items"].update(ITEM, PROJECT, SPRINT, description="")
        assert opener.query()["description"] == ""

    def test_an_empty_change_set_is_rejected(self, services):
        with pytest.raises(UsageError):
            services["items"].update(ITEM, PROJECT, SPRINT)

    def test_assignee_uses_newusers(self, services, opener):
        opener.payloads.extend([USERS_RESPONSE, OK])
        services["items"].update(ITEM, PROJECT, SPRINT, assignee="ada")
        assert json.loads(opener.query()["newusers"]) == [USER]

    def test_targets_the_item(self, services, opener):
        services["items"].update(ITEM, PROJECT, SPRINT, title="x")
        assert f"/item/{ITEM}/" in opener.urls[-1]


class TestDelete:
    def test_issues_a_delete(self, services, opener):
        services["items"].delete(ITEM, PROJECT, SPRINT)
        assert opener.methods == ["DELETE"]


class TestTimeLogs:
    def test_isbillable_is_always_sent(self, services, opener):
        """Zoho rejects the call outright without it (allowedRegex 0|1)."""
        services["timesheets"].log(ITEM, "8:00", PROJECT, SPRINT)

        params = opener.query()
        assert params["isbillable"] == "0"
        assert params["duration"] == "8:00"
        assert params["action"] == "additemlog"

    def test_billable_flag(self, services, opener):
        services["timesheets"].log(ITEM, "1:00", PROJECT, SPRINT, billable=True)
        assert opener.query()["isbillable"] == "1"

    def test_hits_the_timesheet_endpoint(self, services, opener):
        services["timesheets"].log(ITEM, "1:00", PROJECT, SPRINT)
        assert f"/item/{ITEM}/timesheet/" in opener.urls[-1]

    def test_date_is_normalised(self, services, opener):
        services["timesheets"].log(ITEM, "1:00", PROJECT, SPRINT, date="2026-01-05")
        assert opener.query()["date"] == "2026-01-05T00:00:00+0000"

    def test_delete_logs_sends_an_id_array(self, services, opener):
        services["timesheets"].delete_logs(["1", "2"], PROJECT)

        params = opener.query()
        assert opener.methods == ["DELETE"]
        assert json.loads(params["logidarr"]) == ["1", "2"]
        assert params["action"] == "deletelogs"


class TestComments:
    def test_uses_the_working_endpoint(self, services, opener):
        """Zoho's documented /modules/{id}/entity/{item}/notes/ path fails.

        It 401s for every module id, and `addnotes` is rejected as an extra
        parameter. The sprint-scoped path with `name` alone is correct.
        """
        services["comments"].add(ITEM, "looks good", PROJECT, SPRINT)

        url = opener.urls[-1]
        assert f"/sprints/{SPRINT}/item/{ITEM}/notes/" in url
        assert "/modules/" not in url
        assert "addnotes" not in url
        # The field is HTML, so plain text is wrapped before sending.
        assert opener.query()["name"] == "<div>looks good</div>"

    def test_comment_bullets_survive_as_a_list(self, services, opener):
        """Raw newlines render as one run-on paragraph in Zoho."""
        services["comments"].add(
            ITEM, "Done so far:\n- ladder added\n- multiplier dropped",
            PROJECT, SPRINT)

        assert opener.query()["name"] == (
            "<div>Done so far:</div>"
            "<ul><li>ladder added</li><li>multiplier dropped</li></ul>")

    def test_delete_targets_the_note(self, services, opener):
        services["comments"].delete(ITEM, NOTE, PROJECT, SPRINT)

        assert opener.methods == ["DELETE"]
        assert opener.urls[-1].endswith(f"/notes/{NOTE}/")


class TestDryRunAcrossEveryWrite:
    """No write may reach the network when --dry-run is set."""

    @pytest.fixture
    def calls(self, services):
        items = services["items"]
        timesheets = services["timesheets"]
        comments = services["comments"]
        return {
            "create": lambda: items.create("x", PROJECT, SPRINT, dry_run=True),
            "update": lambda: items.update(ITEM, PROJECT, SPRINT, title="x", dry_run=True),
            "delete": lambda: items.delete(ITEM, PROJECT, SPRINT, dry_run=True),
            "log": lambda: timesheets.log(ITEM, "1:00", PROJECT, SPRINT, dry_run=True),
            "delete_logs": lambda: timesheets.delete_logs(["1"], PROJECT, dry_run=True),
            "comment": lambda: comments.add(ITEM, "x", PROJECT, SPRINT, dry_run=True),
            "uncomment": lambda: comments.delete(ITEM, NOTE, PROJECT, SPRINT, dry_run=True),
        }

    @pytest.mark.parametrize("name", [
        "create", "update", "delete", "log", "delete_logs", "comment", "uncomment",
    ])
    def test_makes_no_mutating_request(self, calls, opener, name):
        assert calls[name]() is None
        assert "POST" not in opener.methods
        assert "DELETE" not in opener.methods


class TestAttachments:
    """The only multipart endpoint in the API."""

    @pytest.fixture
    def sample(self, tmp_path):
        path = tmp_path / "screenshot.png"
        path.write_bytes(b"\x89PNG fake")
        return str(path)

    def test_uploads_to_the_plural_path(self, services, opener, sample):
        services["items"].attach(ITEM, [sample], PROJECT, SPRINT)

        assert opener.methods == ["POST"]
        # Add is /attachments/ (plural); delete is /attachment/ (singular).
        assert f"/item/{ITEM}/attachments/" in opener.urls[-1]

    def test_sends_the_mandatory_action(self, services, opener, sample):
        services["items"].attach(ITEM, [sample], PROJECT, SPRINT)
        assert opener.query()["action"] == "attachment"

    def test_a_bad_path_fails_before_the_request(self, services, opener, tmp_path):
        with pytest.raises(UsageError):
            services["items"].attach(ITEM, [str(tmp_path / "gone.png")],
                                     PROJECT, SPRINT)
        assert opener.calls == []

    def test_detach_uses_the_singular_path_and_resource_id(self, services, opener):
        services["items"].detach(ITEM, "99000000000000001", PROJECT, SPRINT)

        assert opener.methods == ["DELETE"]
        assert f"/item/{ITEM}/attachment/" in opener.urls[-1]
        assert opener.query()["docResourceId"] == "99000000000000001"

    def test_dry_run_uploads_nothing(self, services, opener, sample):
        assert services["items"].attach(
            ITEM, [sample], PROJECT, SPRINT, dry_run=True) is None
        assert opener.calls == []


class TestCreateWithAttachments:
    @pytest.fixture
    def sample(self, tmp_path):
        path = tmp_path / "spec.md"
        path.write_text("# spec")
        return str(path)

    def test_creates_then_uploads(self, services, opener, sample):
        opener.payloads.extend([{"addedItemId": ITEM, "status": "success"},
                                OK])
        services["items"].create("x", PROJECT, SPRINT, files=[sample])

        assert len(opener.calls) == 2
        assert "/item/" in opener.urls[0]
        assert "/attachments/" in opener.urls[1]

    def test_files_are_validated_before_the_item_exists(self, services, opener,
                                                        tmp_path):
        """Otherwise a typo leaves an orphan item with nothing attached."""
        with pytest.raises(UsageError):
            services["items"].create("x", PROJECT, SPRINT,
                                     files=[str(tmp_path / "missing.md")])
        assert opener.calls == []

    def test_no_upload_when_creation_returns_no_id(self, services, opener, sample):
        opener.payloads.append({"status": "success"})   # no addedItemId
        services["items"].create("x", PROJECT, SPRINT, files=[sample])
        assert len(opener.calls) == 1
