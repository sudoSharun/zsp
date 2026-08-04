"""``multipart/form-data`` encoding.

Every other write in this client is query parameters with an empty body.
File upload is the exception: Zoho's attachment endpoint wants a real
multipart body, so it gets built here rather than complicating the client.

Written against the stdlib on purpose — pulling in ``requests`` for one
endpoint would cost the package its zero-dependency guarantee.
"""

import mimetypes
import os
import secrets

from ..core.errors import UsageError


class Attachment:
    """One file destined for a multipart body."""

    #: Zoho rejects uploads above this; checked locally to fail fast with a
    #: useful message rather than a 413 halfway through a slow upload.
    MAX_BYTES = 100 * 1024 * 1024

    def __init__(self, path, field="uploadfile"):
        self.path = path
        self.field = field

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def content_type(self):
        guessed, _ = mimetypes.guess_type(self.path)
        return guessed or "application/octet-stream"

    def read(self):
        """Validate and return the file's bytes.

        Checks happen here, before anything is sent, so a bad path in a
        multi-file upload fails without half-uploading the rest.
        """
        if not os.path.exists(self.path):
            raise UsageError(f"File not found: {self.path}")
        if os.path.isdir(self.path):
            raise UsageError(f"Not a file: {self.path}")

        size = os.path.getsize(self.path)
        if size == 0:
            raise UsageError(f"File is empty: {self.path}")
        if size > self.MAX_BYTES:
            raise UsageError(
                f"{self.name} is {size / 1024 / 1024:.1f} MB; "
                f"the limit is {self.MAX_BYTES // 1024 // 1024} MB")

        try:
            with open(self.path, "rb") as handle:
                return handle.read()
        except OSError as error:
            raise UsageError(f"Cannot read {self.path}: {error}") from error

    def __repr__(self):
        return f"<Attachment {self.name!r}>"


class MultipartBody:
    """Builds an RFC 7578 body from text fields and files."""

    def __init__(self, boundary=None):
        # token_hex, not a fixed string: a boundary appearing inside file
        # content would corrupt the request.
        self.boundary = boundary or f"----zsp{secrets.token_hex(16)}"

    @property
    def content_type(self):
        return f"multipart/form-data; boundary={self.boundary}"

    def encode(self, fields=None, attachments=()):
        """Return the encoded body as bytes."""
        parts = []
        marker = f"--{self.boundary}".encode()

        for name, value in (fields or {}).items():
            parts += [
                marker,
                f'Content-Disposition: form-data; name="{name}"'.encode(),
                b"",
                str(value).encode(),
            ]

        for attachment in attachments:
            content = attachment.read()
            parts += [
                marker,
                (f'Content-Disposition: form-data; name="{attachment.field}"; '
                 f'filename="{attachment.name}"').encode(),
                f"Content-Type: {attachment.content_type}".encode(),
                b"",
                content,
            ]

        parts += [f"--{self.boundary}--".encode(), b""]
        return b"\r\n".join(parts)
