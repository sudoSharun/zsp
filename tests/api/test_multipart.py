"""Multipart encoding and file validation."""

import pytest

from zsp.api import Attachment, MultipartBody
from zsp.core import UsageError


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "report.pdf"
    path.write_bytes(b"%PDF-1.4 fake")
    return str(path)


class TestAttachment:
    def test_name_is_the_basename(self, sample):
        assert Attachment(sample).name == "report.pdf"

    def test_content_type_is_guessed(self, sample):
        assert Attachment(sample).content_type == "application/pdf"

    def test_unknown_extension_falls_back_to_octet_stream(self, tmp_path):
        path = tmp_path / "data.zzz"
        path.write_bytes(b"x")
        assert Attachment(str(path)).content_type == "application/octet-stream"

    def test_read_returns_the_bytes(self, sample):
        assert Attachment(sample).read() == b"%PDF-1.4 fake"

    def test_missing_file_is_a_usage_error(self, tmp_path):
        with pytest.raises(UsageError) as caught:
            Attachment(str(tmp_path / "nope.txt")).read()
        assert "File not found" in str(caught.value)
        assert caught.value.exit_code == 2

    def test_directory_is_rejected(self, tmp_path):
        with pytest.raises(UsageError) as caught:
            Attachment(str(tmp_path)).read()
        assert "Not a file" in str(caught.value)

    def test_empty_file_is_rejected(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.touch()
        with pytest.raises(UsageError) as caught:
            Attachment(str(path)).read()
        assert "empty" in str(caught.value)

    def test_oversized_file_is_rejected_before_upload(self, tmp_path, monkeypatch):
        """Fail locally rather than after a slow upload ends in a 413."""
        path = tmp_path / "big.bin"
        path.write_bytes(b"x" * 100)
        monkeypatch.setattr(Attachment, "MAX_BYTES", 10)

        with pytest.raises(UsageError) as caught:
            Attachment(str(path)).read()
        assert "limit" in str(caught.value)


class TestMultipartBody:
    def test_boundary_appears_in_the_content_type(self):
        body = MultipartBody()
        assert body.boundary in body.content_type
        assert body.content_type.startswith("multipart/form-data;")

    def test_boundaries_are_unique_per_instance(self):
        """A fixed boundary occurring inside a file would corrupt the body."""
        assert MultipartBody().boundary != MultipartBody().boundary

    def test_encodes_a_text_field(self):
        body = MultipartBody(boundary="BOUND")
        encoded = body.encode({"action": "attachment"})

        assert b'Content-Disposition: form-data; name="action"' in encoded
        assert b"attachment" in encoded
        assert encoded.endswith(b"--BOUND--\r\n")

    def test_encodes_a_file_with_name_and_type(self, sample):
        body = MultipartBody(boundary="BOUND")
        encoded = body.encode({}, [Attachment(sample)])

        assert b'name="uploadfile"; filename="report.pdf"' in encoded
        assert b"Content-Type: application/pdf" in encoded
        assert b"%PDF-1.4 fake" in encoded

    def test_encodes_fields_and_files_together(self, sample):
        encoded = MultipartBody(boundary="B").encode(
            {"action": "attachment"}, [Attachment(sample)])

        assert encoded.count(b"--B\r\n") == 2   # one part each
        assert b"attachment" in encoded
        assert b"report.pdf" in encoded

    def test_uses_crlf_line_endings(self, sample):
        """RFC 7578 requires CRLF; bare LF is rejected by some servers."""
        encoded = MultipartBody(boundary="B").encode({"a": "1"})
        assert b"\r\n" in encoded
        assert encoded.count(b"\n") == encoded.count(b"\r\n")

    def test_multiple_files(self, tmp_path):
        first = tmp_path / "a.txt"
        second = tmp_path / "b.txt"
        first.write_text("one")
        second.write_text("two")

        encoded = MultipartBody(boundary="B").encode(
            {}, [Attachment(str(first)), Attachment(str(second))])

        assert b'filename="a.txt"' in encoded
        assert b'filename="b.txt"' in encoded

    def test_invalid_file_raises_before_any_encoding(self, tmp_path):
        with pytest.raises(UsageError):
            MultipartBody().encode({}, [Attachment(str(tmp_path / "gone.txt"))])


class TestDryRunValidation:
    """A dry run that accepts a bad path reports success for a command
    that will fail — worse than no dry run at all."""

    def test_dry_run_rejects_a_missing_file(self, client, opener):
        from zsp.core import UsageError

        with pytest.raises(UsageError):
            client.upload("/p/", [Attachment("/tmp/zsp-does-not-exist.png")],
                          dry_run=True, action="attachment")
        assert opener.calls == []

    def test_dry_run_reports_the_size(self, client, sample, capsys):
        client.upload("/p/", [Attachment(sample)], dry_run=True,
                      action="attachment")
        out = capsys.readouterr().out
        assert "bytes" in out
        assert "report.pdf" in out

    def test_dry_run_still_sends_nothing(self, client, opener, sample):
        assert client.upload("/p/", [Attachment(sample)], dry_run=True) is None
        assert opener.calls == []
