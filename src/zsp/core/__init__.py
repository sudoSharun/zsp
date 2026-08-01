"""Foundations: configuration and the exception hierarchy.

Nothing here imports from the rest of the package, so every other layer is
free to depend on it.
"""

from .config import DATA_CENTRES, Config, ConfigStore
from .errors import ApiError, AuthError, LookupError_, UsageError, ZspError

__all__ = [
    "ApiError",
    "AuthError",
    "Config",
    "ConfigStore",
    "DATA_CENTRES",
    "LookupError_",
    "UsageError",
    "ZspError",
]
