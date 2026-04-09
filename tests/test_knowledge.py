"""Tests for KnowledgeStore."""

import json
from datetime import datetime, timezone

from akc_mcp.knowledge import KnowledgeStore, effective_importance


class TestEffectiveImportance:
    def test_unknown_timestamp_penalty(self):
        p = {"importance": 1.0, "distilled": "unknown"}
        assert effective_importance(p) == 0.1

    def test_recent_pattern_no_decay(self):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        p = {"importance": 0.8, "distilled": now}
        result = effective_importance(p)
        assert 0.75 < result <= 0.8

    def test_old_pattern_decays(self):
        p = {"importance": 1.0, "distilled": "2020-01-01T00:00"}
        result = effective_importance(p)
        assert result < 0.1

    def test_bounds(self):
        p = {"importance": 2.0, "distilled": "unknown"}
        result = effective_importance(p)
        assert 0.0 <= result <= 1.0


class TestKnowledgeStore:
    def test_add_and_get(self, tmp_path):
        path = tmp_path / "knowledge.json"
        ks = KnowledgeStore(path=path)
        ks.add_learned_pattern("test pattern", importance=0.7)
        assert ks.pattern_count == 1
        assert ks.get_learned_patterns() == ["test pattern"]

    def test_save_and_load(self, tmp_path):
        path = tmp_path / "knowledge.json"
        ks = KnowledgeStore(path=path)
        ks.add_learned_pattern("pattern 1", category="uncategorized")
        ks.add_learned_pattern("pattern 2", category="constitutional")
        ks.save()

        ks2 = KnowledgeStore(path=path)
        assert ks2.pattern_count == 2
        assert ks2.get_learned_patterns(category="constitutional") == ["pattern 2"]

    def test_get_context_string(self, tmp_path):
        path = tmp_path / "knowledge.json"
        ks = KnowledgeStore(path=path)
        ks.add_learned_pattern("important", importance=0.9)
        ks.add_learned_pattern("less important", importance=0.1)
        ctx = ks.get_context_string(limit=1)
        assert "important" in ctx
        assert "less important" not in ctx

    def test_forbidden_content_filtered(self, tmp_path):
        path = tmp_path / "knowledge.json"
        data = [{"pattern": "my api_key is sk-abc123", "distilled": "unknown", "importance": 0.5, "category": "uncategorized"}]
        path.write_text(json.dumps(data))
        ks = KnowledgeStore(path=path)
        assert ks.pattern_count == 0

    def test_get_learned_patterns_since(self, tmp_path):
        path = tmp_path / "knowledge.json"
        ks = KnowledgeStore(path=path)
        ks.add_learned_pattern("old", distilled="2020-01-01T00:00")
        ks.add_learned_pattern("new", distilled="2026-01-01T00:00")
        result = ks.get_learned_patterns_since("2025-01-01T00:00")
        assert result == ["new"]
