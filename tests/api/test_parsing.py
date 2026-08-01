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


class TestHtmlToText:
    def test_removes_tags(self):
        assert Html.to_text("<div><span>hi</span></div>") == "hi"

    def test_truncates_when_asked(self):
        assert Html.to_text("<p>" + "x" * 100 + "</p>", limit=10) == "x" * 10

    def test_handles_none(self):
        assert Html.to_text(None) == ""


class TestHtmlFromText:
    """Comments and descriptions are HTML fields.

    Sending raw newlines makes Zoho render everything as one run-on
    paragraph — bullets and line breaks silently vanish.
    """

    def test_bullets_become_a_real_list(self):
        html = Html.from_text("- first\n- second")
        assert html == "<ul><li>first</li><li>second</li></ul>"

    def test_asterisk_bullets_work_too(self):
        assert "<ul><li>first</li>" in Html.from_text("* first\n* second")

    def test_numbered_lines_become_an_ordered_list(self):
        html = Html.from_text("1. first\n2. second")
        assert html == "<ol><li>first</li><li>second</li></ol>"

    def test_single_newlines_become_breaks(self):
        assert Html.from_text("one\ntwo") == "<div>one<br>two</div>"

    def test_blank_lines_separate_blocks(self):
        assert Html.from_text("one\n\ntwo") == "<div>one</div><div>two</div>"

    def test_intro_line_then_bullets(self):
        """The shape that actually broke: a lead-in followed by a list."""
        html = Html.from_text("Done so far:\n- ladder added\n- multiplier dropped")
        assert html == ("<div>Done so far:</div>"
                        "<ul><li>ladder added</li><li>multiplier dropped</li></ul>")

    def test_list_then_trailing_paragraph(self):
        html = Html.from_text("- one\n- two\nStill verifying.")
        assert html == ("<ul><li>one</li><li>two</li></ul>"
                        "<div>Still verifying.</div>")

    def test_switching_list_type_starts_a_new_list(self):
        html = Html.from_text("- bullet\n1. numbered")
        assert html == "<ul><li>bullet</li></ul><ol><li>numbered</li></ol>"

    def test_special_characters_are_escaped(self):
        """Stray angle brackets must not become markup."""
        assert Html.from_text("a < b & c > d") == "<div>a &lt; b &amp; c &gt; d</div>"

    def test_escaping_applies_inside_list_items(self):
        assert Html.from_text("- a & b") == "<ul><li>a &amp; b</li></ul>"

    def test_text_that_contains_real_tags_is_treated_as_markup(self):
        """Documented trade-off of the pass-through above.

        Someone writing a literal "<b>" in prose gets it rendered rather
        than escaped. Rare enough to accept, and it is what makes
        hand-written HTML possible.
        """
        assert Html.from_text("<b>bold</b>") == "<b>bold</b>"

    def test_empty_string_passes_through(self):
        """An empty description is how the field gets cleared."""
        assert Html.from_text("") == ""

    def test_none_passes_through(self):
        assert Html.from_text(None) is None

    def test_existing_html_is_left_alone(self):
        """Callers who hand-write markup keep control of it."""
        markup = "<div>already <strong>done</strong></div>"
        assert Html.from_text(markup) == markup

    def test_round_trips_back_to_readable_text(self):
        original = "Done so far:\n- ladder added\n- multiplier dropped"
        assert Html.to_text(Html.from_text(original)) == (
            "Done so far: ladder added multiplier dropped")

    def test_indented_bullets_are_recognised(self):
        assert Html.from_text("  - indented") == "<ul><li>indented</li></ul>"
