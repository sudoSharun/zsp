"""Each command end to end, through the parser, against a stub transport."""

import json

import pytest

from ..conftest import (
    ITEM,
    ITEMS_RESPONSE,
    NOTE,
    NOTES_RESPONSE,
    OK,
    PROJECT,
    PROJECTS_RESPONSE,
    SPRINT,
    SPRINTS_RESPONSE,
    STATUS_RESPONSE,
    TEAMS_RESPONSE,
    TIMESHEET_RESPONSE,
    USERS_RESPONSE,
)


@pytest.fixture
def run(interface, opener):
    """Run a command line, returning (exit code, printed lines)."""
    def invoke(argv, payloads=()):
        opener.payloads.extend(payloads)
        printed = []
        interface.application.renderer_sink = printed
        code = interface.run(argv)
        return code, printed
    return invoke


class TestReadCommands:
    def test_teams(self, interface, opener, capsys):
        opener.payloads.append(TEAMS_RESPONSE)
        assert interface.run(["teams"]) == 0
        assert "acme" in capsys.readouterr().out

    def test_projects(self, interface, opener, capsys):
        opener.payloads.append(PROJECTS_RESPONSE)
        interface.run(["projects"])
        assert "Apollo" in capsys.readouterr().out

    def test_sprints(self, interface, opener, capsys):
        opener.payloads.append(SPRINTS_RESPONSE)
        interface.run(["sprints", "--project", PROJECT])
        assert "Sprint 1" in capsys.readouterr().out

    def test_items(self, interface, opener, capsys):
        opener.payloads.extend([ITEMS_RESPONSE, STATUS_RESPONSE])
        interface.run(["items", "--project", PROJECT, "--sprint", SPRINT])
        assert "Fix login" in capsys.readouterr().out

    def test_items_json_is_parseable(self, interface, opener, capsys):
        opener.payloads.extend([ITEMS_RESPONSE, STATUS_RESPONSE])
        interface.run(["items", "--project", PROJECT, "--sprint", SPRINT, "--json"])
        rows = json.loads(capsys.readouterr().out)
        assert rows[0]["title"] == "Fix login"

    def test_item_detail(self, interface, opener, capsys):
        opener.payloads.append({"itemJObj": {}, "status": "success"})
        interface.run(["item", ITEM, "--project", PROJECT, "--sprint", SPRINT])
        assert "status" in capsys.readouterr().out

    def test_standup(self, interface, opener, capsys):
        opener.payloads.append(TIMESHEET_RESPONSE)
        interface.run(["standup", "--project", PROJECT, "--days", "100000"])
        assert "did the thing" in capsys.readouterr().out

    def test_comments(self, interface, opener, capsys):
        opener.payloads.append(NOTES_RESPONSE)
        interface.run(["comments", ITEM, "--project", PROJECT, "--sprint", SPRINT])
        assert "Looks good to me" in capsys.readouterr().out


class TestWriteCommands:
    def test_create(self, interface, opener, capsys):
        opener.payloads.append(OK)
        code = interface.run(["create", "--title", "New", "--project", PROJECT,
                              "--sprint", SPRINT])
        assert code == 0
        assert "Created" in capsys.readouterr().out
        assert opener.methods == ["POST"]

    def test_create_dry_run_sends_nothing(self, interface, opener, capsys):
        code = interface.run(["create", "--title", "New", "--project", PROJECT,
                              "--sprint", SPRINT, "--dry-run"])
        assert code == 0
        assert opener.calls == []
        assert "DRY RUN" in capsys.readouterr().out

    def test_update(self, interface, opener, capsys):
        opener.payloads.extend([STATUS_RESPONSE, OK])
        interface.run(["update", ITEM, "--project", PROJECT, "--sprint", SPRINT,
                       "--status", "Done"])
        assert "Updated" in capsys.readouterr().out

    def test_update_requires_a_field(self, interface, capsys):
        code = interface.run(["update", ITEM, "--project", PROJECT,
                              "--sprint", SPRINT])
        assert code == 2
        assert "Nothing to update" in capsys.readouterr().err

    def test_log(self, interface, opener, capsys):
        opener.payloads.append(OK)
        interface.run(["log", ITEM, "--duration", "8:00", "--project", PROJECT,
                       "--sprint", SPRINT])
        assert "Logged on" in capsys.readouterr().out

    def test_comment(self, interface, opener, capsys):
        opener.payloads.append(OK)
        interface.run(["comment", ITEM, "--text", "hi", "--project", PROJECT,
                       "--sprint", SPRINT])
        assert "Commented on" in capsys.readouterr().out

    def test_uncomment(self, interface, opener, capsys):
        opener.payloads.append(OK)
        interface.run(["uncomment", ITEM, NOTE, "--project", PROJECT,
                       "--sprint", SPRINT])
        assert opener.methods == ["DELETE"]

    def test_rm(self, interface, opener, capsys):
        opener.payloads.append(OK)
        interface.run(["rm", ITEM, "--project", PROJECT, "--sprint", SPRINT])
        assert opener.methods == ["DELETE"]

    def test_assignee_name_is_resolved(self, interface, opener):
        opener.payloads.extend([USERS_RESPONSE, OK])
        interface.run(["create", "--title", "x", "--assignee", "ada",
                       "--project", PROJECT, "--sprint", SPRINT])
        assert "users" in opener.query()


class TestSessionCommands:
    def test_use_saves_defaults(self, interface, tmp_store, capsys):
        assert interface.run(["use", PROJECT, SPRINT]) == 0

        saved = tmp_store.load()
        assert saved.default_project == PROJECT
        assert saved.default_sprint == SPRINT
        assert "Default project" in capsys.readouterr().out

    def test_use_project_only(self, interface, tmp_store):
        interface.run(["use", PROJECT])
        assert tmp_store.load().default_project == PROJECT

    def test_saved_defaults_make_ids_optional(self, interface, tmp_store, opener):
        interface.run(["use", PROJECT, SPRINT])
        opener.payloads.extend([ITEMS_RESPONSE, STATUS_RESPONSE])

        assert interface.run(["items"]) == 0
        assert PROJECT in opener.urls[0]

    def test_config_redacts_secrets(self, interface, capsys):
        interface.run(["config"])
        out = capsys.readouterr().out
        assert "***redacted***" in out
        assert "testsecret" not in out

    def test_logout_removes_the_file(self, interface, tmp_store, capsys):
        assert interface.run(["logout"]) == 0
        assert not tmp_store.exists()
        assert "Logged out" in capsys.readouterr().out

    def test_logout_when_absent_says_so(self, interface, tmp_store, capsys):
        tmp_store.delete()
        interface.run(["logout"])
        assert "Not logged in" in capsys.readouterr().out
