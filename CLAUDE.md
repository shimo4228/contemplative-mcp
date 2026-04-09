# AKC MCP

MCP server providing AKC (Agent Knowledge Cycle) cognitive tools — distillation, constitution, self-improvement. contemplative-agent の認知層を独立パッケージとして再実装。

## Tech Stack

- Python 3.10+, hatch (build), uv (package manager)
- mcp (FastMCP), anthropic (LLM backend)
- pytest, pytest-asyncio (testing)

## Structure

```
src/akc_mcp/
  server.py         # FastMCP server (7 tools, 5 resources)
  llm.py            # Anthropic API backend
  config.py         # Paths, security constants
  knowledge.py      # KnowledgeStore (JSON, time-decay importance)
  episode_log.py    # EpisodeLog (JSONL, append-only)
  identity.py       # Identity read/write
  distill.py        # Sleep-time distillation pipeline
  insight.py        # Skill extraction from patterns
  rules.py          # Rule distillation from skills
  constitution.py   # Constitution management + amendment
  stocktake.py      # Skills/rules quality audit
  prompts/          # LLM prompt templates (*.md)
tests/              # pytest suite
```

## Build / Test / Run

```bash
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Test
uv run pytest tests/ -v
uv run pytest tests/ --cov=akc_mcp --cov-report=term-missing

# Run MCP server (stdio)
export ANTHROPIC_API_KEY=sk-...
akc-mcp

# Or via module
python -m akc_mcp.server
```

## Conventions

- Data directory: `~/.config/akc/` (env: `AKC_HOME`)
- Data format: contemplative-agent 完全互換 (knowledge.json, identity.md, JSONL logs)
- All tools are read-only (dry_run / result return only). No file writes via MCP
- Forbidden pattern validation on all content
- Path traversal prevention on template resources

## Design Decisions

- **別リポジトリ**: contemplative-agent は "Security by Absence" が思想。MCP は外部 LLM 前提で思想が異なるため分離
- **Anthropic API only**: Ollama 非依存。ユーザーは API キーだけで利用可能
- **承認ゲート**: 蒸留結果は返却のみ、書き込みは行わない (ADR-0012 準拠)
- **プロンプト互換**: contemplative-agent と同じプロンプトテンプレートを使用

## Related

- [contemplative-agent](https://github.com/shimo4228/contemplative-agent) — ローカル完結版 (Ollama + Moltbook)
- [contemplative-agent-rules](https://github.com/shimo4228/contemplative-agent-rules) — 四公理ルール
- Laukkonen et al. (2025) Contemplative Artificial Intelligence. arXiv:2504.15125

## Status

Phase 1 (stdio MCP server) — 実装完了、テスト通過
