"""Decoding Zoho's positional-array response format.

Zoho Sprints does not return named objects. A list response looks like::

    {
      "itemJObj":  {"<id>": ["Fix login", "117", ...]},
      "item_prop": {"itemName": 0, "itemNo": 1, ...},
      "userDisplayName": {"<user id>": "Ada Lovelace"}
    }

Rows are bare arrays; ``*_prop`` maps field name to array index. That map
is per-response, so decoding must read it rather than hardcode positions —
Zoho orders fields differently between endpoints.
"""

import re


class ZohoDate:
    """Date formats Zoho will accept on writes."""

    BARE = re.compile(r"\d{4}-\d{2}-\d{2}")
    SUFFIX = "T00:00:00+0000"

    @classmethod
    def normalise(cls, value):
        """Pad a bare ``YYYY-MM-DD`` to the format Zoho demands.

        Writes otherwise fail with *"Only yyyy-MM-dd'T'HH:mm:ssZZ will be
        allowed"*. Anything already carrying a time passes through so an
        explicit timestamp still wins.

        Zoho interprets the result in the **portal's** timezone regardless
        of the offset sent, so a stored value can read as the previous day
        in UTC. That is expected, not a bug.
        """
        if value and cls.BARE.fullmatch(value):
            return value + cls.SUFFIX
        return value


class Html:
    """Zoho stores comments and log notes as HTML fragments."""

    TAG = re.compile("<[^>]+>")

    @classmethod
    def to_text(cls, text, limit=None):
        clean = cls.TAG.sub("", text or "").strip()
        return clean[:limit] if limit else clean


class Response:
    """Wraps one API payload and decodes its positional rows."""

    def __init__(self, payload):
        self.payload = payload or {}

    def __getitem__(self, key):
        return self.payload[key]

    def get(self, key, default=None):
        return self.payload.get(key, default)

    @property
    def display_names(self):
        """``{user id: display name}`` shipped alongside most list responses."""
        return self.payload.get("userDisplayName") or {}

    @property
    def has_more(self):
        return bool(self.payload.get("next") or self.payload.get("hasNext"))

    def rows(self, rows_key, prop_key, fields):
        """Decode ``*JObj`` / ``*_prop`` into a list of dicts.

        ``fields`` maps output key -> Zoho field name. Unknown or
        out-of-range fields come back as ``None`` rather than raising,
        because Zoho omits trailing fields on some rows.
        """
        prop = self.payload.get(prop_key) or {}
        raw = self.payload.get(rows_key) or {}

        decoded = []
        for row_id, values in raw.items():
            row = {"id": row_id}
            for out_key, field in fields.items():
                index = prop.get(field)
                row[out_key] = (values[index]
                                if index is not None and index < len(values)
                                else None)
            decoded.append(row)
        return decoded

    def name_for(self, ids):
        """Resolve a user id, or list of ids, to display names."""
        lookup = self.display_names
        if isinstance(ids, list):
            return ",".join(lookup.get(i, i) for i in ids)
        return lookup.get(ids, ids) if ids else ids
