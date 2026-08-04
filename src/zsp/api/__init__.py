"""Transport: OAuth, HTTP and response decoding.

This layer knows how to talk to Zoho but nothing about sprints or items —
that meaning lives in :mod:`zsp.services`.
"""

from .auth import Authenticator, OAuthCallbackHandler
from .client import SprintsClient
from .multipart import Attachment, MultipartBody
from .parsing import Html, Response, ZohoDate

__all__ = [
    "Attachment",
    "Authenticator",
    "Html",
    "MultipartBody",
    "OAuthCallbackHandler",
    "Response",
    "SprintsClient",
    "ZohoDate",
]
