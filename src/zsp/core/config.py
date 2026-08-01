"""Configuration: the in-memory :class:`Config` and its file store.

Credentials and persistence are deliberately separate — :class:`Config`
knows nothing about disks, :class:`ConfigStore` knows nothing about OAuth.
"""

import json
import os
import stat

from .errors import AuthError, UsageError

DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/zsp")

#: Zoho data centres, in the order ``zsp login`` offers them.
DATA_CENTRES = ("in", "com", "eu", "com.au", "jp")


class Config:
    """Credentials, cached token and per-user defaults."""

    SECRET_FIELDS = frozenset({"client_secret", "refresh_token", "access_token"})

    def __init__(self, client_id, client_secret, refresh_token, dc,
                 access_token=None, access_token_expiry=0,
                 team_id=None, default_project=None, default_sprint=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.dc = dc
        self.access_token = access_token
        self.access_token_expiry = access_token_expiry
        self.team_id = team_id
        self.default_project = default_project
        self.default_sprint = default_sprint

    @classmethod
    def from_dict(cls, data):
        known = {
            "client_id", "client_secret", "refresh_token", "dc", "access_token",
            "access_token_expiry", "team_id", "default_project", "default_sprint",
        }
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self):
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "dc": self.dc,
            "access_token": self.access_token,
            "access_token_expiry": self.access_token_expiry,
            "team_id": self.team_id,
            "default_project": self.default_project,
            "default_sprint": self.default_sprint,
        }

    def redacted(self):
        """A copy safe to print — secrets replaced with a marker."""
        return {
            key: ("***redacted***" if key in self.SECRET_FIELDS and value else value)
            for key, value in self.to_dict().items()
        }

    def resolve(self, project=None, sprint=None, need_sprint=True):
        """Apply saved defaults, raising if a required scope is still unset."""
        project = project or self.default_project
        sprint = sprint or self.default_sprint
        if not project:
            raise UsageError(self._missing("project", "--project"))
        if need_sprint and not sprint:
            raise UsageError(self._missing("sprint", "--sprint"))
        return project, sprint

    @staticmethod
    def _missing(what, flag):
        return (f"No {what} given. Pass {flag}, or save a default with: "
                f"zsp use <project> [sprint]")

    def __repr__(self):
        return f"<Config dc={self.dc!r} project={self.default_project!r}>"


class ConfigStore:
    """Reads and writes ``~/.config/zsp/config.json`` at mode 0600."""

    def __init__(self, directory=None):
        self.directory = (directory or os.environ.get("ZSP_CONFIG_DIR")
                          or DEFAULT_CONFIG_DIR)

    @property
    def path(self):
        return os.path.join(self.directory, "config.json")

    def exists(self):
        return os.path.exists(self.path)

    def load(self):
        if not self.exists():
            raise AuthError("Not logged in. Run: zsp login")
        with open(self.path) as handle:
            return Config.from_dict(json.load(handle))

    def save(self, config):
        os.makedirs(self.directory, exist_ok=True)
        with open(self.path, "w") as handle:
            json.dump(config.to_dict(), handle, indent=2)
        os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        return config

    def delete(self):
        """Remove stored credentials. True if there were any."""
        if self.exists():
            os.remove(self.path)
            return True
        return False

    def set_defaults(self, project=None, sprint=None):
        config = self.load()
        if project:
            config.default_project = project
        if sprint:
            config.default_sprint = sprint
        return self.save(config)
