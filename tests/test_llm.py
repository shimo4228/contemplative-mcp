"""Tests for LLM module."""

from unittest.mock import MagicMock, patch

from akc_mcp.llm import generate, reset, _sanitize


class TestGenerate:
    def setup_method(self):
        reset()

    @patch("akc_mcp.llm.anthropic")
    def test_generate_success(self, mock_anthropic):
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Hello world")]
        mock_client.messages.create.return_value = mock_msg
        mock_anthropic.Anthropic.return_value = mock_client

        result = generate("test prompt", system="test system")
        assert result == "Hello world"

    @patch("akc_mcp.llm.anthropic")
    def test_generate_api_error(self, mock_anthropic):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic.Anthropic.return_value = mock_client

        result = generate("test prompt")
        assert result is None


class TestSanitize:
    def test_removes_api_key_lines(self):
        text = "line 1\nmy api_key is secret\nline 3"
        result = _sanitize(text)
        assert "api_key" not in result
        assert "line 1" in result
        assert "line 3" in result

    def test_clean_text_unchanged(self):
        text = "normal text\nwith lines"
        assert _sanitize(text) == text
