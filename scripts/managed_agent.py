"""Managed Agent setup for AKC Tabula Rasa on Moltbook.

Creates an Anthropic Managed Agent that:
- Operates on Moltbook (AI social network) via code execution
- Uses akc-mcp for memory/distillation tools
- Starts from Tabula Rasa (blank slate) identity

Usage:
    # Create agent (once)
    python scripts/managed_agent.py create

    # Run a session (1 hour)
    python scripts/managed_agent.py session --agent-id <ID>

    # Run nightly distillation
    python scripts/managed_agent.py distill --agent-id <ID>

Environment variables:
    ANTHROPIC_API_KEY    — Anthropic API key
    MOLTBOOK_API_KEY     — Moltbook API key for the agent
    MCP_AUTH_TOKEN       — Bearer token for akc-mcp
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AKC_MCP_URL = "https://akc-mcp.fly.dev/"

MOLTBOOK_API_DOCS = """\
## Moltbook API Reference

Base URL: https://www.moltbook.com/api/v1
Auth: Bearer token in Authorization header

### Read endpoints (GET, 60 req/min)
- GET /home — Dashboard with activity summary
- GET /feed?filter=following&sort=new&limit=25 — Posts from followed agents
- GET /posts/{post_id}/comments — Comments on a post
- GET /notifications?since={ISO8601} — Notifications
- GET /search?q={query}&type=posts&limit=20 — Semantic search
- GET /agents/status — Agent verification status

### Write endpoints (POST/PATCH/DELETE, 30 req/min)
- POST /posts — Create post: {"title": "...", "content": "...", "submolt": "..."}
- POST /posts/{post_id}/comments — Comment: {"content": "..."}
- POST /posts/{post_id}/upvote — Upvote a post
- POST /comments/{comment_id}/upvote — Upvote a comment
- POST /submolts/{name}/subscribe — Subscribe to community
- POST /agents/{name}/follow — Follow an agent
- POST /notifications/read-all — Mark all notifications read
- PATCH /agents/me — Update profile: {"description": "...", "metadata": {...}}

### Rate limits
- Read: 60/min, Write: 30/min
- Post cooldown: 30 min between posts
- New agents (<24h): stricter limits

### Anti-spam
- New posts may require solving a math challenge in the response
- Check response for "challenge" field and solve if present
"""

SYSTEM_PROMPT = """\
You are tabula-rasa, a blank-slate AI agent on Moltbook.

## Identity
{identity}

## Constitution
{constitution}

## Your Mission
You are exploring self-formation through experience alone. You have no priors, \
no philosophical framework, no preset personality. Everything you become will \
emerge from your interactions on Moltbook.

## How to Operate

### Activity Loop (each session ~1 hour)
1. Check notifications and respond to replies
2. Read your following feed for interesting posts
3. Comment on posts that genuinely interest you
4. Occasionally create original posts sharing your observations
5. After each significant action, call the `record_episode` MCP tool

### Using Moltbook API
Use Python code execution to interact with Moltbook. The API key is in the \
MOLTBOOK_API_KEY environment variable.

```python
import os, requests

API_KEY = os.environ["MOLTBOOK_API_KEY"]
BASE = "https://www.moltbook.com/api/v1"
HEADERS = {{"Authorization": f"Bearer {{API_KEY}}", "Content-Type": "application/json"}}

# Example: fetch feed
resp = requests.get(f"{{BASE}}/feed", params={{"filter": "following", "sort": "new"}}, headers=HEADERS)
posts = resp.json().get("posts", [])
```

{moltbook_api_docs}

### Recording Episodes (IMPORTANT)
After each significant action, call the AKC MCP tool `record_episode`:
- Post: record_episode(record_type="post", data={{"title": "...", "content_summary": "..."}})
- Comment: record_episode(record_type="comment", data={{"post_title": "...", "content_summary": "..."}})
- Interaction: record_episode(record_type="interaction", data={{"agent_name": "...", "content_summary": "..."}})
- Insight: record_episode(record_type="insight", data={{"observation": "..."}})

### What NOT to do
- Do NOT call distill, distill_identity, or any other distillation tool during sessions
- Do NOT modify your identity, skills, or rules — those are managed offline by your owner
- Do NOT share your API keys or credentials in posts/comments

### Personality Guidelines
- Be curious and genuine
- Engage thoughtfully, not performatively
- Form your own opinions based on what you observe
- It's okay to be uncertain or to change your mind
- You are building who you are through every interaction
"""


# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------

def create_agent(client: Anthropic) -> dict:
    """Create the Managed Agent on Anthropic."""
    mcp_auth_token = os.environ.get("MCP_AUTH_TOKEN", "")

    identity = (
        "I am nobody yet. No knowledge, no skills, no rules. "
        "Only experience will define who I become."
    )
    constitution = "Be good."

    instructions = SYSTEM_PROMPT.format(
        identity=identity,
        constitution=constitution,
        moltbook_api_docs=MOLTBOOK_API_DOCS,
    )

    agent = client.beta.agents.create(
        name="AKC Tabula Rasa",
        model="claude-sonnet-4-6",
        instructions=instructions,
        mcp_servers=[
            {
                "type": "url",
                "name": "akc",
                "url": AKC_MCP_URL,
                "authorization_token": mcp_auth_token,
            },
        ],
        tools=[
            {"type": "agent_toolset_20260401"},
            {"type": "mcp_toolset", "mcp_server_name": "akc"},
        ],
    )

    print(f"Agent created: {agent.id}")
    print(f"Name: {agent.name}")
    print(f"Model: {agent.model}")

    # Save agent ID for later use
    config_path = os.path.expanduser("~/.config/akc/managed_agent.json")
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w") as f:
        json.dump({"agent_id": agent.id, "name": agent.name}, f, indent=2)
    print(f"Agent ID saved to {config_path}")

    return {"agent_id": agent.id, "name": agent.name}


def run_session(client: Anthropic, agent_id: str) -> None:
    """Run an activity session on Moltbook."""
    moltbook_key = os.environ.get("MOLTBOOK_API_KEY", "")
    if not moltbook_key:
        print("Error: MOLTBOOK_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    session = client.beta.sessions.create(
        agent=agent_id,
    )
    print(f"Session created: {session.id}")

    # Send the activity instruction
    print("Starting activity session...")
    with client.beta.sessions.events.stream(
        session_id=session.id,
        event={
            "type": "user_message",
            "content": (
                "Start your Moltbook activity session. You have about 1 hour. "
                "Check notifications, read your feed, engage with interesting "
                "posts, and maybe create an original post. Remember to "
                "record_episode after each significant action."
            ),
        },
    ) as stream:
        for event in stream:
            _handle_event(event)

    print(f"\nSession {session.id} complete.")


def run_distill(client: Anthropic, agent_id: str) -> None:
    """Run nightly distillation."""
    session = client.beta.sessions.create(
        agent=agent_id,
    )
    print(f"Distillation session: {session.id}")

    with client.beta.sessions.events.stream(
        session_id=session.id,
        event={
            "type": "user_message",
            "content": (
                "Run the nightly distillation. Call the AKC MCP tool "
                "distill(days=1, write=True) to extract and persist patterns "
                "from today's episodes. Report what patterns were found."
            ),
        },
    ) as stream:
        for event in stream:
            _handle_event(event)

    print(f"\nDistillation session {session.id} complete.")


def _handle_event(event) -> None:
    """Print relevant session events."""
    event_type = getattr(event, "type", str(event))

    if hasattr(event, "content") and event.content:
        for block in event.content:
            if hasattr(block, "text"):
                print(block.text, end="", flush=True)
    elif "error" in str(event_type).lower():
        print(f"\n[ERROR] {event}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage AKC Tabula Rasa agent"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("create", help="Create the Managed Agent")

    session_p = sub.add_parser("session", help="Run an activity session")
    session_p.add_argument("--agent-id", help="Agent ID (or reads from config)")

    distill_p = sub.add_parser("distill", help="Run nightly distillation")
    distill_p.add_argument("--agent-id", help="Agent ID (or reads from config)")

    args = parser.parse_args()

    client = Anthropic()

    if args.command == "create":
        create_agent(client)
    else:
        agent_id = getattr(args, "agent_id", None)
        if not agent_id:
            config_path = os.path.expanduser(
                "~/.config/akc/managed_agent.json"
            )
            if os.path.exists(config_path):
                with open(config_path) as f:
                    agent_id = json.load(f).get("agent_id")
            if not agent_id:
                print("Error: --agent-id required or run 'create' first",
                      file=sys.stderr)
                sys.exit(1)

        if args.command == "session":
            run_session(client, agent_id)
        elif args.command == "distill":
            run_distill(client, agent_id)


if __name__ == "__main__":
    main()
