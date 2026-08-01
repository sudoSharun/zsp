"""Response decoding, date normalisation and HTML stripping."""

from zsp.api import Html, Response, ZohoDate


class TestResponseRows:
    def test_maps_fields_by_prop_index(self):
        response = Response({
            "xJObj": {"id1": ["Fix login", "117", 5]},
            "x_prop": {"itemName": 0, "itemNo": 1, "points": 2},
        })
        rows = response.rows("xJObj", "x_prop",
                             {"title": "itemName", "points": "points"})
        assert rows == [{"id": "id1", "title": "Fix login", "points": 5}]

    def test_tolerates_short_rows(self):
        """Zoho omits trailing fields on some rows; that must not raise."""
        response = Response({"xJObj": {"id1": ["only"]}, "x_prop": {"a": 0, "b": 9}})
        assert response.rows("xJObj", "x_prop", {"a": "a", "b": "b"}) == [
            {"id": "id1", "a": "only", "b": None}
        ]

    def test_unknown_field_name_yields_none(self):
        response = Response({"xJObj": {"id1": ["v"]}, "x_prop": {"a": 0}})
        assert response.rows("xJObj", "x_prop", {"nope": "missing"}) == [
            {"id": "id1", "nope": None}
        ]

    def test_missing_keys_yield_no_rows(self):
        assert Response({}).rows("xJObj", "x_prop", {"a": "a"}) == []

    def test_explicit_nulls_yield_no_rows(self):
        """Some endpoints send null rather than omitting the key."""
        response = Response({"xJObj": None, "x_prop": None})
        assert response.rows("xJObj", "x_prop", {"a": "a"}) == []

    def test_empty_payload_is_safe(self):
        assert Response(None).rows("x", "y", {}) == []


class TestResponseNames:
    def test_resolves_a_list_of_ids(self):
        response = Response({"userDisplayName": {"1": "Ada", "2": "Grace"}})
        assert response.name_for(["1", "2"]) == "Ada,Grace"

    def test_resolves_a_single_id(self):
        assert Response({"userDisplayName": {"1": "Ada"}}).name_for("1") == "Ada"

    def test_passes_unknown_ids_through(self):
        assert Response({}).name_for(["99"]) == "99"

    def test_handles_empty(self):
        assert Response({}).name_for(None) is None


class TestResponseMetadata:
    def test_has_more_reads_next(self):
        assert Response({"next": True}).has_more is True

    def test_has_more_reads_has_next(self):
        assert Response({"hasNext": True}).has_more is True

    def test_has_more_defaults_false(self):
        assert Response({}).has_more is False

    def test_get_with_default(self):
        assert Response({}).get("missing", "fallback") == "fallback"


class TestZohoDate:
    def test_pads_a_bare_date(self):
        """Zoho: 'Only yyyy-MM-dd'T'HH:mm:ssZZ will be allowed'."""
        assert ZohoDate.normalise("2026-01-05") == "2026-01-05T00:00:00+0000"

    def test_leaves_full_timestamps_alone(self):
        stamp = "2026-01-05T09:30:00+0530"
        assert ZohoDate.normalise(stamp) == stamp

    def test_passes_through_empty(self):
        assert ZohoDate.normalise(None) is None
        assert ZohoDate.normalise("") == ""

    def test_ignores_non_date_text(self):
        assert ZohoDate.normalise("tomorrow") == "tomorrow"


class TestHtml:
    def test_removes_tags(self):
        assert Html.to_text("<div><span>hi</span></div>") == "hi"

    def test_truncates_when_asked(self):
        assert Html.to_text("<p>" + "x" * 100 + "</p>", limit=10) == "x" * 10

    def test_handles_none(self):
        assert Html.to_text(None) == ""
