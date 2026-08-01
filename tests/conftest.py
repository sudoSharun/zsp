"""Shared fixtures.

Every response body here mirrors the *shape* Zoho really returns
(positional arrays plus a ``*_prop`` index map) but all ids, names and
emails are fabricated. No real workspace data is in this repository.
"""

import json
from urllib.parse import parse_qs, urlparse

import pytest

from zsp.api import SprintsClient
from zsp.cli import Application, CommandLineInterface
from zsp.core import Config, ConfigStore
from zsp.services import (
    CommentService,
    ItemService,
    LookupService,
    ProjectService,
    SprintService,
    TimesheetService,
    WorkspaceService,
)

TEAM = "10000000000000001"
PROJECT = "20000000000000002"
SPRINT = "30000000000000003"
ITEM = "40000000000000004"
USER = "50000000000000005"
NOTE = "60000000000000006"

STATUS_TODO = "70000000000000007"
STATUS_DOING = "70000000000000008"
STATUS_DONE = "70000000000000009"
TYPE_BUG = "80000000000000003"
PRIORITY_HIGH = "90000000000000002"


class FakeResponse:
    """Minimal stand-in for the object urlopen returns."""

    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class RecordingOpener:
    """Replaces urlopen: records every request, replays queued payloads."""

    def __init__(self, payloads=()):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, request):
        self.calls.append({
            "url": request.full_url,
            "method": request.get_method(),
        })
        payload = self.payloads.pop(0) if self.payloads else {"status": "success"}
        return FakeResponse(payload)

    # -- assertions helpers ----------------------------------------------

    @property
    def urls(self):
        return [call["url"] for call in self.calls]

    @property
    def methods(self):
        return [call["method"] for call in self.calls]

    def query(self, index=-1):
        """Parsed query parameters of the nth recorded call."""
        # keep_blank_values: `--desc ""` sends description= and the
        # assertion for it must not silently vanish.
        parsed = parse_qs(urlparse(self.urls[index]).query, keep_blank_values=True)
        return {key: value[0] for key, value in parsed.items()}

    def find_query(self, containing):
        """Query params of the first call whose params include ``containing``."""
        for index in range(len(self.calls)):
            params = self.query(index)
            if containing in params:
                return params
        raise AssertionError(f"no recorded call carried {containing!r}")


class StubAuthenticator:
    """Returns a token without ever contacting Zoho Accounts."""

    def __init__(self, token="test-token"):
        self.token = token
        self.calls = 0

    def access_token(self, config):
        self.calls += 1
        return self.token


@pytest.fixture
def config():
    return Config(
        client_id="1000.TESTCLIENTID",
        client_secret="testsecret",
        refresh_token="1000.testrefresh",
        dc="in",
        access_token="1000.testaccess",
        access_token_expiry=4_102_444_800,  # far future; never refreshes
        team_id=TEAM,
    )


@pytest.fixture
def opener():
    """A fresh recorder. Queue payloads with ``opener.payloads.extend(...)``."""
    return RecordingOpener()


@pytest.fixture
def client(config, opener):
    return SprintsClient(config, StubAuthenticator(), opener=opener)


@pytest.fixture
def services(client, config):
    """All services sharing one client, as the real Application wires them."""
    lookups = LookupService(client, config)
    return {
        "lookups": lookups,
        "workspaces": WorkspaceService(client, config),
        "projects": ProjectService(client, config),
        "sprints": SprintService(client, config),
        "items": ItemService(client, config, lookups),
        "timesheets": TimesheetService(client, config, lookups),
        "comments": CommentService(client, config),
    }


@pytest.fixture
def tmp_store(tmp_path, config):
    """A ConfigStore in a temp dir, pre-populated so commands can run."""
    store = ConfigStore(str(tmp_path))
    store.save(config)
    return store


@pytest.fixture
def application(tmp_store, config, client):
    """A fully wired Application with the network stubbed out."""
    return Application(store=tmp_store, config=config, client=client,
                       authenticator=StubAuthenticator())


@pytest.fixture
def interface(application):
    return CommandLineInterface(application)


# --- response fixtures -------------------------------------------------

TEAMS_RESPONSE = {
    "portals": [{"zsoid": TEAM, "teamName": "acme"}],
    "status": "success",
}

PROJECTS_RESPONSE = {
    "projectJObj": {PROJECT: ["Apollo", "12", "2026-01-01T00:00:00.000Z",
                              "2026-06-30T00:00:00.000Z", 0, "", "", "", 1]},
    "project_prop": {"projName": 0, "projNo": 1, "startDate": 2,
                     "endDate": 3, "estimationType": 4, "status": 8},
    "next": False,
    "status": "success",
}

SPRINTS_RESPONSE = {
    "sprintJObj": {SPRINT: ["Sprint 1", "2026-01-01T00:00:00.000Z",
                            "2026-01-14T00:00:00.000Z", "-1", "10d", 2]},
    "sprint_prop": {"sprintName": 0, "startDate": 1, "endDate": 2,
                    "completedOn": 3, "duration": 4, "sprintType": 5},
    "next": False,
    "status": "success",
}

STATUS_RESPONSE = {
    "statusJObj": {
        STATUS_TODO: ["To do", True, "", 0, 0],
        STATUS_DOING: ["In progress", True, "", 50, 2],
        STATUS_DONE: ["Done", True, "", 100, 1],
    },
    "status_prop": {"statusName": 0, "isDefault": 1, "statusDescription": 2,
                    "statusPercentage": 3, "statusType": 4},
    "status": "success",
}

ITEMS_RESPONSE = {
    "itemJObj": {ITEM: ["Fix login", "117", USER, "2d", "0",
                        STATUS_DOING, [USER], 5]},
    "item_prop": {"itemName": 0, "itemNo": 1, "createdBy": 2, "duration": 3,
                  "depth": 4, "statusId": 5, "ownerId": 6, "points": 7},
    "userDisplayName": {USER: "Ada Lovelace"},
    "next": False,
    "status": "success",
}

USERS_RESPONSE = {
    "userJObj": {USER: ["Ada Lovelace", "ada@example.com", True, "600001", 1]},
    "user_prop": {"displayName": 0, "emailId": 1, "isConfirmed": 2,
                  "iamUserId": 3, "userStatus": 4},
    "next": False,
    "status": "success",
}

ITEM_TYPES_RESPONSE = {
    "projItemTypeJObj": {
        "80000000000000001": ["x", "Story", True, "0", 2],
        "80000000000000002": ["x", "Task", True, "1", 0],
        TYPE_BUG: ["x", "Bug", True, "2", 1],
    },
    "projItemType_prop": {"itemTypeId": 0, "itemTypeName": 1, "isDefault": 2,
                          "sequence": 3, "baseType": 4},
    "status": "success",
}

PRIORITIES_RESPONSE = {
    "projPriorityJObj": {
        "90000000000000001": ["None", True, "x", "", "#000", "0"],
        PRIORITY_HIGH: ["High", False, "x", "", "#f00", "3"],
    },
    "projPriority_prop": {"priorityName": 0, "isDefault": 1, "priorityId": 2,
                          "priorityDescription": 3, "colorCode": 4, "sequence": 5},
    "next": False,
    "status": "success",
}

TIMESHEET_RESPONSE = {
    "logJObj": {
        "11000000000000001": [SPRINT, "117", "Fix login", "0", 0, 0, "", "",
                              ITEM, "11000000000000001", "", USER,
                              "2026-01-05T00:00:00.000Z", "28800000", 1, 0,
                              "", USER, "<div>did the thing</div>"],
    },
    "log_prop": {"sprintId": 0, "itemNo": 1, "itemName": 2, "isIntegrated": 3,
                 "tagCount": 5, "itemBlockId": 6, "epicId": 7, "itemId": 8,
                 "tLogId": 9, "releaseId": 10, "Owner": 11, "logDate": 12,
                 "logTime": 13, "billableType": 14, "approveType": 15,
                 "addedBy": 17, "logNotes": 18},
    "userDisplayName": {USER: "Ada Lovelace"},
    "hasNext": False,
    "status": "success",
}

NOTES_RESPONSE = {
    "notesJObj": {NOTE: [NOTE, "Looks good to me", USER,
                         "2026-01-06T00:00:00.000Z", USER,
                         "2026-01-06T00:00:00.000Z"]},
    "notes_prop": {"noteId": 0, "notes": 1, "createdBy": 2, "createdOn": 3,
                   "updatedBy": 4, "updatedOn": 5},
    "userDisplayName": {USER: "Ada Lovelace"},
    "next": False,
    "status": "success",
}

OK = {"status": "success"}
