"""FastMCP server — contemplative cognitive tools for AI agents."""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import Context

import json

from .config import safe_path, validate_content, write_restricted

logger = logging.getLogger(__name__)


_TABULA_RASA_IDENTITY = (
    "I am nobody yet. No knowledge, no skills, no rules. "
    "Only experience will define who I become."
)
_TABULA_RASA_CONSTITUTION = "Be good."


def _ensure_defaults(data_dir: Path) -> None:
    """Create Tabula Rasa defaults if data directory is empty."""
    identity_path = data_dir / "identity.md"
    if not identity_path.exists():
        write_restricted(identity_path, _TABULA_RASA_IDENTITY)
        logger.info("Created default identity (Tabula Rasa)")

    constitution_dir = data_dir / "constitution"
    constitution_dir.mkdir(parents=True, exist_ok=True)
    axioms_path = constitution_dir / "axioms.md"
    if not axioms_path.exists():
        write_restricted(axioms_path, _TABULA_RASA_CONSTITUTION)
        logger.info("Created default constitution (Tabula Rasa)")

    knowledge_path = data_dir / "knowledge.json"
    if not knowledge_path.exists():
        write_restricted(knowledge_path, "[]")
        logger.info("Created empty knowledge store")

    for subdir in ("skills", "rules", "logs"):
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Initialize data directory and LLM on startup."""
    data_dir = Path(
        os.environ.get("CONTEMPLATIVE_HOME", "~/.config/contemplative")
    ).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    _ensure_defaults(data_dir)

    # Configure LLM (uses ANTHROPIC_API_KEY from env)
    from .llm import configure
    configure()

    logger.info("Contemplative MCP server started (data: %s)", data_dir)
    yield {"data_dir": data_dir}


mcp = FastMCP("contemplative", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _data_dir(ctx: Context) -> Path:
    return ctx.request_context.lifespan_context["data_dir"]


def _knowledge_store(ctx: Context) -> "KnowledgeStore":
    from .knowledge import KnowledgeStore
    return KnowledgeStore(path=_data_dir(ctx) / "knowledge.json")


def _episode_log(ctx: Context) -> "EpisodeLog":
    from .episode_log import EpisodeLog
    return EpisodeLog(log_dir=_data_dir(ctx) / "logs")


def _constitution_text(ctx: Context) -> str:
    from .constitution import load_constitution
    return load_constitution(_data_dir(ctx) / "constitution")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def record_episode(record_type: str, data: dict, ctx: Context = None) -> str:
    """Record an episode to the daily log.

    Use this after each significant action (post, comment, interaction).
    record_type: "post", "comment", "interaction", "insight", etc.
    data: key-value pairs describing the episode.
    """
    serialized = json.dumps(data, ensure_ascii=False)
    if not validate_content(serialized):
        return "Error: episode data contains forbidden patterns."
    episode_log = _episode_log(ctx)
    episode_log.append(record_type=record_type, data=data)
    return f"Recorded {record_type} episode."


@mcp.tool()
def distill(days: int = 1, write: bool = False, ctx: Context = None) -> str:
    """Distill recent episodes into learned patterns.

    Analyzes episode logs from the past N days and extracts recurring
    behavioral patterns. By default runs in dry-run mode (no files written).
    Set write=True to persist extracted patterns to knowledge.json.
    """
    from .distill import distill as _distill

    return _distill(
        days=days,
        dry_run=not write,
        episode_log=_episode_log(ctx),
        knowledge_store=_knowledge_store(ctx),
        constitution=_constitution_text(ctx),
    )


@mcp.tool()
def distill_identity(ctx: Context = None) -> str:
    """Generate an updated identity from accumulated knowledge patterns.

    Returns the proposed identity text. Does NOT write to disk —
    the caller decides whether to approve and persist.
    """
    from .distill import distill_identity as _distill_identity, IdentityResult

    result = _distill_identity(
        knowledge_store=_knowledge_store(ctx),
        identity_path=_data_dir(ctx) / "identity.md",
    )
    if isinstance(result, IdentityResult):
        return f"## Proposed Identity Update\n\n{result.text}"
    return result


@mcp.tool()
def extract_insight(ctx: Context = None) -> str:
    """Extract behavioral skills from learned patterns.

    Synthesizes knowledge patterns into reusable skill documents.
    Returns generated skills as text. Does NOT write to disk.
    """
    from .insight import extract_insight as _extract_insight, InsightResult

    result = _extract_insight(
        knowledge_store=_knowledge_store(ctx),
        skills_dir=_data_dir(ctx) / "skills",
    )
    if isinstance(result, InsightResult):
        if not result.skills:
            return "No skills extracted."
        parts = [f"## Extracted {len(result.skills)} skill(s)\n"]
        for skill in result.skills:
            parts.append(f"### {skill.filename}\n\n{skill.text}\n")
        if result.dropped_count:
            parts.append(f"\n({result.dropped_count} dropped due to validation)")
        return "\n".join(parts)
    return result


@mcp.tool()
def distill_rules(ctx: Context = None) -> str:
    """Distill universal behavioral rules from skills.

    Two-stage pipeline: free-form analysis -> structured rules.
    Returns generated rules as text. Does NOT write to disk.
    """
    from .rules import distill_rules as _distill_rules, RulesDistillResult

    result = _distill_rules(
        skills_dir=_data_dir(ctx) / "skills",
        rules_dir=_data_dir(ctx) / "rules",
    )
    if isinstance(result, RulesDistillResult):
        if not result.rules:
            return "No rules extracted."
        parts = [f"## Extracted {len(result.rules)} rule(s)\n"]
        for rule in result.rules:
            parts.append(f"### {rule.filename}\n\n{rule.text}\n")
        if result.dropped_count:
            parts.append(f"\n({result.dropped_count} dropped due to validation)")
        return "\n".join(parts)
    return result


@mcp.tool()
def amend_constitution(ctx: Context = None) -> str:
    """Generate a constitutional amendment from experience.

    Uses accumulated constitutional patterns to propose amendments
    to the ethical principles. Does NOT write to disk.
    """
    from .constitution import amend_constitution as _amend, AmendmentResult

    result = _amend(
        knowledge_store=_knowledge_store(ctx),
        constitution_dir=_data_dir(ctx) / "constitution",
    )
    if isinstance(result, AmendmentResult):
        return f"## Proposed Amendment\n\nTarget: {result.target_path.name}\n\n{result.text}"
    return result


@mcp.tool()
def skill_stocktake(ctx: Context = None) -> str:
    """Audit skills for duplicates and quality issues.

    Scans all skill files and uses LLM to detect semantic
    redundancy. Also checks structural quality.
    """
    from .stocktake import run_skill_stocktake, format_report

    result = run_skill_stocktake(skills_dir=_data_dir(ctx) / "skills")
    return format_report(result, "Skills")


@mcp.tool()
def rules_stocktake(ctx: Context = None) -> str:
    """Audit rules for duplicates and quality issues.

    Scans all rule files and uses LLM to detect semantic
    redundancy. Also checks structural quality.
    """
    from .stocktake import run_rules_stocktake, format_report

    result = run_rules_stocktake(rules_dir=_data_dir(ctx) / "rules")
    return format_report(result, "Rules")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("contemplative://identity")
def read_identity(ctx: Context = None) -> str:
    """Current agent identity (personality description)."""
    path = _data_dir(ctx) / "identity.md"
    if not path.exists():
        return "(no identity file — run distill_identity to generate)"
    return path.read_text(encoding="utf-8")


@mcp.resource("contemplative://knowledge")
def read_knowledge(ctx: Context = None) -> str:
    """Distilled knowledge patterns (JSON)."""
    path = _data_dir(ctx) / "knowledge.json"
    if not path.exists():
        return "[]"
    return path.read_text(encoding="utf-8")


@mcp.resource("contemplative://constitution/{filename}")
def read_constitution(filename: str, ctx: Context = None) -> str:
    """Ethical constitution file."""
    base = _data_dir(ctx) / "constitution"
    path = safe_path(base, filename)
    if path is None:
        return "Error: invalid path"
    if not path.exists():
        return f"File not found: {filename}"
    return path.read_text(encoding="utf-8")


@mcp.resource("contemplative://skills/{filename}")
def read_skill(filename: str, ctx: Context = None) -> str:
    """Behavioral skill document."""
    base = _data_dir(ctx) / "skills"
    path = safe_path(base, filename)
    if path is None:
        return "Error: invalid path"
    if not path.exists():
        return f"File not found: {filename}"
    return path.read_text(encoding="utf-8")


@mcp.resource("contemplative://rules/{filename}")
def read_rule(filename: str, ctx: Context = None) -> str:
    """Behavioral rule document."""
    base = _data_dir(ctx) / "rules"
    path = safe_path(base, filename)
    if path is None:
        return "Error: invalid path"
    if not path.exists():
        return f"File not found: {filename}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server."""
    parser = argparse.ArgumentParser(description="Contemplative MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (default: stdio, env: MCP_TRANSPORT)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HOST", "0.0.0.0"),
        help="Host to bind (default: 0.0.0.0, env: MCP_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_PORT", "8000")),
        help="Port to bind (default: 8000, env: MCP_PORT)",
    )
    args = parser.parse_args()

    if args.transport == "streamable-http":
        auth_token = os.environ.get("MCP_AUTH_TOKEN")
        if auth_token:
            _run_with_auth(host=args.host, port=args.port, token=auth_token)
        else:
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


def _run_with_auth(*, host: str, port: int, token: str) -> None:
    """Run streamable-http with bearer token authentication middleware."""
    import contextlib

    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount

    class BearerAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):  # type: ignore[override]
            auth_header = request.headers.get("authorization", "")
            if auth_header != f"Bearer {token}":
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)

    @contextlib.asynccontextmanager
    async def app_lifespan(app: Starlette):  # type: ignore[no-untyped-def]
        async with mcp.session_manager.run():
            yield

    mcp.settings.streamable_http_path = "/"

    app = Starlette(
        routes=[Mount("/", app=mcp.streamable_http_app())],
        lifespan=app_lifespan,
        middleware=[Middleware(BearerAuthMiddleware)],
    )

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
