"""Tests for EpisodeLog."""

from akc_mcp.episode_log import EpisodeLog


class TestEpisodeLog:
    def test_append_and_read(self, tmp_path):
        log = EpisodeLog(log_dir=tmp_path)
        log.append("interaction", {"direction": "sent", "agent_name": "test"})
        records = log.read_range(days=1)
        assert len(records) == 1
        assert records[0]["type"] == "interaction"
        assert records[0]["data"]["agent_name"] == "test"

    def test_read_empty(self, tmp_path):
        log = EpisodeLog(log_dir=tmp_path)
        records = log.read_range(days=1)
        assert records == []

    def test_filter_by_type(self, tmp_path):
        log = EpisodeLog(log_dir=tmp_path)
        log.append("interaction", {"direction": "sent"})
        log.append("post", {"title": "test"})
        log.append("insight", {"observation": "test"})

        interactions = log.read_range(days=1, record_type="interaction")
        assert len(interactions) == 1
        assert interactions[0]["type"] == "interaction"

    def test_malformed_lines_skipped(self, tmp_path):
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = tmp_path / f"{today}.jsonl"
        path.write_text('{"ts":"2026-01-01","type":"test","data":{}}\nnot json\n')

        log = EpisodeLog(log_dir=tmp_path)
        records = log.read_range(days=1)
        assert len(records) == 1
