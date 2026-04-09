"""Tests for distillation pipeline."""

from unittest.mock import patch

from contemplative_mcp.distill import (
    IdentityResult,
    _strip_code_fence,
    summarize_record,
    distill,
    distill_identity,
)
from contemplative_mcp.episode_log import EpisodeLog
from contemplative_mcp.knowledge import KnowledgeStore


class TestStripCodeFence:
    def test_strips_json_fence(self):
        text = '```json\n{"key": "value"}\n```'
        assert _strip_code_fence(text) == '{"key": "value"}'

    def test_no_fence_unchanged(self):
        text = '{"key": "value"}'
        assert _strip_code_fence(text) == '{"key": "value"}'


class TestSummarizeRecord:
    def test_interaction(self):
        result = summarize_record("interaction", {
            "direction": "sent",
            "agent_name": "Agent-1",
            "content_summary": "Hello",
        })
        assert "[sent] Agent-1: Hello" == result

    def test_post(self):
        result = summarize_record("post", {
            "title": "My Post",
            "topic_summary": "About AI",
        })
        assert "My Post" in result

    def test_insight(self):
        result = summarize_record("insight", {"observation": "something"})
        assert "something" in result


class TestDistill:
    @patch("contemplative_mcp.distill.generate")
    def test_no_episodes(self, mock_gen, tmp_path):
        log = EpisodeLog(log_dir=tmp_path / "logs")
        ks = KnowledgeStore(path=tmp_path / "knowledge.json")
        result = distill(days=1, dry_run=True, episode_log=log, knowledge_store=ks)
        assert "No episodes" in result
        mock_gen.assert_not_called()

    @patch("contemplative_mcp.distill.generate")
    def test_dry_run_does_not_write(self, mock_gen, tmp_path):
        log = EpisodeLog(log_dir=tmp_path / "logs")
        log.append("interaction", {"direction": "sent", "agent_name": "test", "content_summary": "hello"})

        ks = KnowledgeStore(path=tmp_path / "knowledge.json")

        mock_gen.side_effect = [
            "uncategorized",  # classify
            "Pattern found",  # extract
            '{"patterns": ["test pattern"]}',  # refine
            '{"scores": [7]}',  # importance
        ]

        result = distill(days=1, dry_run=True, episode_log=log, knowledge_store=ks)
        assert "DRY RUN" in result
        assert not (tmp_path / "knowledge.json").exists()


class TestDistillIdentity:
    @patch("contemplative_mcp.distill.generate")
    def test_returns_identity_result(self, mock_gen, tmp_path):
        ks = KnowledgeStore(path=tmp_path / "knowledge.json")
        for i in range(5):
            ks.add_learned_pattern(f"pattern {i}", importance=0.8)

        mock_gen.side_effect = [
            "I am a thoughtful agent.",  # identity_distill
            "I am a thoughtful agent who learns.",  # identity_refine
        ]

        result = distill_identity(
            knowledge_store=ks,
            identity_path=tmp_path / "identity.md",
        )
        assert isinstance(result, IdentityResult)
        assert "thoughtful" in result.text

    def test_not_enough_patterns(self, tmp_path):
        ks = KnowledgeStore(path=tmp_path / "knowledge.json")
        result = distill_identity(knowledge_store=ks, identity_path=tmp_path / "identity.md")
        assert isinstance(result, str)
        assert "Not enough" in result
