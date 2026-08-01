"""Read paths across the workspace, project, sprint, item and log services."""

import json

import pytest

from zsp.core import LookupError_, UsageError

from ..conftest import (
    ITEM,
    ITEMS_RESPONSE,
    NOTES_RESPONSE,
    PROJECT,
    PROJECTS_RESPONSE,
    SPRINT,
    SPRINTS_RESPONSE,
    STATUS_RESPONSE,
    TEAM,
    TEAMS_RESPONSE,
    TIMESHEET_RESPONSE,
    USER,
    USERS_RESPONSE,
)


class TestWorkspaces:
    def test_lists_id_and_name(self, services, opener):
        opener.payloads.append(TEAMS_RESPONSE)
        assert services["workspaces"].list() == [{"id": TEAM, "name": "acme"}]

    def test_team_id_uses_the_configured_value(self, services, opener):
        assert services["workspaces"].team == TEAM
        assert opener.calls == [], "a configured team id should skip the call"

    def test_team_id_falls_back_to_the_first_workspace(self, services, opener, config):
        config.team_id = None
        opener.payloads.append(TEAMS_RESPONSE)
        assert services["workspaces"].team == TEAM

    def test_team_id_is_cached_after_lookup(self, services, opener, config):
        config.team_id = None
        opener.payloads.append(TEAMS_RESPONSE)
        first = services["workspaces"].team
        second = services["workspaces"].team
        assert first == second
        assert len(opener.calls) == 1

    def test_no_workspaces_raises(self, services, opener, config):
        config.team_id = None
        opener.payloads.append({"portals": []})
        with pytest.raises(LookupError_):
            _ = services["workspaces"].team


class TestProjects:
    def test_decodes_positional_rows(self, services, opener):
        opener.payloads.append(PROJECTS_RESPONSE)
        rows = services["projects"].list()
        assert rows[0]["name"] == "Apollo"
        assert rows[0]["status"] == 1

    def test_backlog_id(self, services, opener):
        opener.payloads.append({"backlogId": "999", "status": "success"})
        assert services["projects"].backlog_id(PROJECT) == "999"


class TestSprints:
    def test_sends_the_mandatory_type_filter(self, services, opener):
        """Without type=[1,2,3,4] this endpoint returns nothing at all."""
        opener.payloads.append(SPRINTS_RESPONSE)
        rows = services["sprints"].list(PROJECT)

        assert rows[0]["name"] == "Sprint 1"
        assert opener.query()["type"] == "[1,2,3,4]"

    def test_requires_a_project(self, services):
        with pytest.raises(UsageError) as caught:
            services["sprints"].list()
        assert "zsp use" in str(caught.value)

    def test_uses_the_saved_default_project(self, services, opener, config):
        config.default_project = PROJECT
        opener.payloads.append(SPRINTS_RESPONSE)
        services["sprints"].list()
        assert PROJECT in opener.urls[0]


class TestItems:
    def test_resolves_status_and_assignee(self, services, opener):
        opener.payloads.extend([ITEMS_RESPONSE, STATUS_RESPONSE])
        rows = services["items"].list(PROJECT, SPRINT)

        assert rows[0]["title"] == "Fix login"
        assert rows[0]["status"] == "In progress"
        assert rows[0]["assignee"] == "Ada Lovelace"
        assert rows[0]["points"] == 5

    def test_unknown_status_id_falls_back_to_the_id(self, services, opener):
        opener.payloads.extend([ITEMS_RESPONSE, {"statusJObj": {}, "status_prop": {}}])
        assert services["items"].list(PROJECT, SPRINT)[0]["status"]

    def test_assignee_filter_is_applied_server_side(self, services, opener):
        """Regression: filtering names locally only ever saw page one."""
        opener.payloads.extend([USERS_RESPONSE, ITEMS_RESPONSE, STATUS_RESPONSE])
        services["items"].list(PROJECT, SPRINT, assignee="ada")

        params = opener.find_query("filter")
        assert json.loads(params["filter"])["I-owner"] == [USER]

    def test_unknown_assignee_raises_before_any_write(self, services, opener):
        opener.payloads.append(USERS_RESPONSE)
        with pytest.raises(LookupError_):
            services["items"].list(PROJECT, SPRINT, assignee="nobody")

    def test_requires_project_and_sprint(self, services):
        with pytest.raises(UsageError):
            services["items"].list(PROJECT, None)

    def test_detail_requests_the_details_action(self, services, opener):
        opener.payloads.append({"status": "success"})
        services["items"].get(ITEM, PROJECT, SPRINT)
        assert opener.query()["action"] == "details"


class TestTimesheets:
    def test_converts_millis_and_strips_html(self, services, opener):
        opener.payloads.append(TIMESHEET_RESPONSE)
        rows = services["timesheets"].recent(PROJECT, days=100_000)

        assert rows[0]["hours"] == 8.0
        assert rows[0]["notes"] == "did the thing"
        assert rows[0]["owner"] == "Ada Lovelace"

    def test_applies_the_day_window(self, services, opener):
        """The fixture log is dated 2026-01-05, outside a one-day window."""
        opener.payloads.append(TIMESHEET_RESPONSE)
        assert services["timesheets"].recent(PROJECT, days=1) == []

    def test_skips_unparseable_dates(self, services, opener):
        broken = dict(TIMESHEET_RESPONSE, logJObj={"1": [None] * 19})
        opener.payloads.append(broken)
        assert services["timesheets"].recent(PROJECT, days=100_000) == []


class TestComments:
    def test_reads_from_notesjobj(self, services, opener):
        """The read key is notesJObj; the write response uses itemnotesJObj."""
        opener.payloads.append(NOTES_RESPONSE)
        rows = services["comments"].list(ITEM, PROJECT, SPRINT)

        assert rows[0]["text"] == "Looks good to me"
        assert rows[0]["author"] == "Ada Lovelace"

    def test_hits_the_working_endpoint(self, services, opener):
        opener.payloads.append(NOTES_RESPONSE)
        services["comments"].list(ITEM, PROJECT, SPRINT)

        url = opener.urls[0]
        assert f"/sprints/{SPRINT}/item/{ITEM}/notes/" in url
        assert "/modules/" not in url


class TestStatusList:
    """Regression: statuses were being inferred from items in use, so a
    configured-but-empty board column was invisible."""

    def test_lists_every_configured_status(self, services, opener):
        opener.payloads.append(STATUS_RESPONSE)
        rows = services["lookups"].status_rows(PROJECT)

        assert [r["name"] for r in rows] == ["To do", "In progress", "Done"]

    def test_labels_the_status_kind(self, services, opener):
        opener.payloads.append(STATUS_RESPONSE)
        by_name = {r["name"]: r["kind"] for r in services["lookups"].status_rows(PROJECT)}

        assert by_name["To do"] == "open"
        assert by_name["Done"] == "closed"
        assert by_name["In progress"] == "in progress"

    def test_hits_the_itemstatus_endpoint(self, services, opener):
        opener.payloads.append(STATUS_RESPONSE)
        services["lookups"].status_rows(PROJECT)
        assert "/itemstatus/" in opener.urls[0]

    def test_requires_a_project(self, services):
        with pytest.raises(UsageError):
            services["lookups"].status_rows()
