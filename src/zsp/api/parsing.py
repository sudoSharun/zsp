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
    """Zoho stores comments, descriptions and log notes as HTML fragments.

    Both directions matter. Reading, the markup has to come off. Writing,
    plain text has to go *in* as HTML — send raw newlines and Zoho renders
    the whole thing as one run-on paragraph, because that is what HTML does
    with whitespace.
    """

    TAG = re.compile("<[^>]+>")

    #: A line that is a bullet: "- x", "* x" or "• x".
    BULLET = re.compile(r"^\s*[-*•]\s+(.*)$")
    #: A line that is numbered: "1. x" or "1) x".
    NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
    #: Enough to tell that the caller already sent markup.
    LOOKS_LIKE_HTML = re.compile(r"<(div|p|br|ul|ol|li|span|strong|em|b|i)\b[^>]*>",
                                 re.IGNORECASE)

    #: Tags that end a line of prose. Without turning these into spaces,
    #: "<div>one</div><div>two</div>" strips to "onetwo".
    BLOCK_END = re.compile(r"</?(br|div|p|li|ul|ol|tr|h[1-6])\b[^>]*>",
                           re.IGNORECASE)

    @classmethod
    def to_text(cls, text, limit=None):
        """Strip markup for terminal display, keeping words separated."""
        spaced = cls.BLOCK_END.sub(" ", text or "")
        clean = re.sub(r"\s+", " ", cls.TAG.sub("", spaced)).strip()
        return clean[:limit] if limit else clean

    @classmethod
    def from_text(cls, text):
        """Convert plain text — with markdown-style lists — to HTML.

        Blank lines separate blocks, single newlines become ``<br>``, and
        runs of ``-``/``*``/``•`` or ``1.`` lines become real lists.

        An empty string is returned untouched, because that is how a
        description gets cleared. Text that already contains markup is
        passed through, so callers can hand-write HTML if they want to.
        """
        if not text or cls.LOOKS_LIKE_HTML.search(text):
            return text

        blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
        return "".join(cls._block(b) for b in blocks if b.strip())

    @classmethod
    def _block(cls, block):
        rendered = []
        pending = []          # consecutive plain lines
        items = []            # consecutive list items
        tag = None            # "ul" or "ol" for the run being collected

        def flush_text():
            if pending:
                rendered.append("<div>" + "<br>".join(pending) + "</div>")
                pending.clear()

        def flush_list():
            nonlocal tag
            if items:
                cells = "".join(f"<li>{i}</li>" for i in items)
                rendered.append(f"<{tag}>{cells}</{tag}>")
                items.clear()
            tag = None

        for line in block.split("\n"):
            bullet = cls.BULLET.match(line)
            numbered = cls.NUMBERED.match(line)

            if bullet or numbered:
                wanted = "ul" if bullet else "ol"
                if tag and tag != wanted:
                    flush_list()
                flush_text()
                tag = wanted
                items.append(cls.escape((bullet or numbered).group(1).strip()))
            elif line.strip():
                flush_list()
                pending.append(cls.escape(line.strip()))

        flush_list()
        flush_text()
        return "".join(rendered)

    @staticmethod
    def escape(text):
        """Escape the three characters that would otherwise become markup."""
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))


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
