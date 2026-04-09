"""Tests for config module."""

from contemplative_mcp.config import safe_path, validate_content, write_restricted


class TestValidateContent:
    def test_clean_content(self):
        assert validate_content("This is normal text") is True

    def test_api_key_detected(self):
        assert validate_content("my api_key is here") is False

    def test_bearer_token_detected(self):
        assert validate_content("Bearer eyJhbG...") is False

    def test_github_token_detected(self):
        assert validate_content("token ghp_abcdefghijklmnopqrstuvwxyz1234567890") is False

    def test_rsa_key_detected(self):
        assert validate_content("-----BEGIN RSA PRIVATE KEY-----") is False


class TestSafePath:
    def test_valid_path(self, tmp_path):
        result = safe_path(tmp_path, "file.md")
        assert result == (tmp_path / "file.md").resolve()

    def test_traversal_rejected(self, tmp_path):
        result = safe_path(tmp_path, "../../../etc/passwd")
        assert result is None

    def test_absolute_path_rejected(self, tmp_path):
        result = safe_path(tmp_path, "/etc/passwd")
        assert result is None


class TestWriteRestricted:
    def test_writes_content(self, tmp_path):
        path = tmp_path / "test.txt"
        write_restricted(path, "hello")
        assert path.read_text() == "hello"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "test.txt"
        write_restricted(path, "hello")
        assert path.read_text() == "hello"
