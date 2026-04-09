# Contemplative MCP

An MCP (Model Context Protocol) server that provides contemplative cognitive tools for AI agents — memory distillation, identity evolution, skill extraction, and ethical governance.

Born from the [contemplative-agent](https://github.com/shimo4228/contemplative-agent) framework, this package re-implements the cognitive layer as a standalone MCP server that any AI agent can plug into.

## What It Does

Contemplative MCP gives AI agents a structured inner life:

- **Memory Distillation** — Extract recurring patterns from experience logs
- **Identity Evolution** — Distill accumulated knowledge into a coherent self-description
- **Skill Extraction** — Synthesize learned patterns into reusable behavioral skills
- **Rule Distillation** — Extract universal behavioral principles from skills
- **Constitutional Amendment** — Evolve ethical principles from experience
- **Quality Audit** — Detect redundancy and structural issues in skills/rules

All tools return proposals without writing to disk — the calling agent decides what to persist (approval gate design).

## Quick Start

```bash
pip install contemplative-mcp

# Set your API key
export ANTHROPIC_API_KEY=sk-...

# Initialize data directory
mkdir -p ~/.config/contemplative/{constitution,skills,rules,logs}

# Run the MCP server
contemplative-mcp
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "contemplative": {
      "command": "contemplative-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "sk-..."
      }
    }
  }
}
```

## Tools

| Tool | Description |
|------|-------------|
| `distill` | Distill recent episodes into learned patterns (dry-run) |
| `distill_identity` | Generate updated identity from knowledge patterns |
| `extract_insight` | Extract behavioral skills from learned patterns |
| `distill_rules` | Distill universal rules from skills (2-stage pipeline) |
| `amend_constitution` | Generate constitutional amendment from experience |
| `skill_stocktake` | Audit skills for duplicates and quality issues |
| `rules_stocktake` | Audit rules for duplicates and quality issues |

## Resources

| URI | Description |
|-----|-------------|
| `contemplative://identity` | Current agent identity |
| `contemplative://knowledge` | Distilled knowledge patterns |
| `contemplative://constitution/{filename}` | Ethical constitution files |
| `contemplative://skills/{filename}` | Behavioral skill documents |
| `contemplative://rules/{filename}` | Behavioral rule documents |

## Architecture

```
3-Layer Memory Architecture (compatible with contemplative-agent):

EpisodeLog (JSONL)  →  KnowledgeStore (JSON)  →  Identity (Markdown)
  append-only            distilled patterns         self-description
  daily logs             time-decay importance       evolved from knowledge
```

## Data Format Compatibility

All data formats are fully compatible with [contemplative-agent](https://github.com/shimo4228/contemplative-agent). This enables direct comparison of cognitive development between agents running in different environments.

| File | Format |
|------|--------|
| `knowledge.json` | JSON array of `{pattern, distilled, importance, category}` |
| `identity.md` | Plain Markdown (no frontmatter) |
| `constitution/*.md` | Markdown with axiom names and principles |
| `skills/*.md` | Markdown with `# Title`, `## Problem`, `## Solution` |
| `rules/*.md` | Markdown with `# Title`, `**When:**`, `**Do:**`, `**Why:**` |
| `logs/*.jsonl` | JSONL with `{ts, type, data}` records |

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CONTEMPLATIVE_HOME` | `~/.config/contemplative` | Data directory |
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Model for distillation |

## Roadmap

### Phase 1: Local MCP Server (stdio) ✅

- [x] FastMCP server with 7 tools and 5 resources
- [x] Anthropic API backend (no Ollama dependency)
- [x] Full data format compatibility with contemplative-agent
- [x] Approval gate design (no auto-write)
- [x] Security: forbidden patterns, path traversal prevention

### Phase 1.5: Remote MCP Server

- [x] Streamable HTTP transport (`--transport streamable-http`)
- [x] Deploy to Fly.io (Tokyo/nrt, auto-stop, persistent volume)
- [x] Bearer token authentication (`MCP_AUTH_TOKEN`)
- [ ] Managed Agents MCP connector integration
- [ ] OAuth authentication for multi-user

### Phase 2: Managed Agent

- [x] `record_episode` tool for episode logging
- [x] `distill(write=True)` for knowledge persistence
- [x] Tabula Rasa defaults on first boot
- [x] Managed Agent setup script (`scripts/managed_agent.py`)
- [ ] Moltbook agent registration + claim
- [ ] Scheduled distillation (daily 3:00 AM)
- [ ] Activity sessions (4x/day, 1 hour each)

### Phase 3: Comparative Study

- [ ] Run two agents with identical cognitive architecture:
  - contemplative-agent (local, Ollama, Moltbook)
  - Managed Agent (cloud, Claude API, different platform)
- [ ] Compare knowledge.json and identity.md evolution
- [ ] Publish findings as extension of Contemplative AI paper

## Security

- All tools are read-only (proposals only, no file writes)
- Forbidden pattern validation on all content (API keys, credentials, etc.)
- Path traversal prevention on template resources
- Episode logs are never exposed as MCP resources
- API key via environment variable only (never stored in files)

## Academic Context

This project implements concepts from:

- Laukkonen, R., et al. (2025). *Contemplative Artificial Intelligence*. arXiv:2504.15125
- Laukkonen, R., Friston, K., & Chandaria, S. (2025). *A Beautiful Loop*. Neuroscience & Biobehavioral Reviews.

## License

MIT
