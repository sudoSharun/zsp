"""Exception hierarchy.

The CLI catches :class:`ZspError` at the top level and maps it to an exit
code, so nothing below ``cli.py`` calls ``sys.exit``. That keeps every
function importable and unit-testable.
"""


class ZspError(Exception):
    """Base for every error this package raises. Exit code 1."""

    exit_code = 1


class UsageError(ZspError):
    """Bad or missing arguments — nothing was sent anywhere."""

    exit_code = 2


class AuthError(ZspError):
    """Not logged in, or the refresh token was rejected."""

    exit_code = 3


class ApiError(ZspError):
    """Zoho returned a non-2xx response."""

    exit_code = 4

    def __init__(self, status, body, url=None):
        self.status = status
        self.body = body
        self.url = url
        super().__init__(f"API error {status}: {body[:300]}")


class LookupError_(ZspError):
    """A human-readable name could not be resolved to an id."""

    exit_code = 5
