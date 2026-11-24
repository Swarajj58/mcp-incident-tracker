from __future__ import annotations

import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_git_forensics_stdio_discovery_and_resource() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "incident_mcp.servers.git_forensics_server"],
        cwd=str(PROJECT_ROOT),
    )
    async with Client(params) as client:
        tools_res = await client.list_tools()
        tool_names = {t.name for t in getattr(tools_res, "tools", tools_res)}
        assert "get_commit_diff" in tool_names
        assert "get_file_blame" in tool_names

        commits_res = await client.read_resource("git://recent-commits")
        text = "\n".join(
            item.text for item in getattr(commits_res, "contents", []) if hasattr(item, "text")
        )
        assert "3db8b9f" in text or "discount_tier" in text


@pytest.mark.asyncio
async def test_runbook_stdio_prompt_and_search() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "incident_mcp.servers.runbook_server"],
        cwd=str(PROJECT_ROOT),
    )
    async with Client(params) as client:
        prompts_res = await client.list_prompts()
        prompt_names = {p.name for p in getattr(prompts_res, "prompts", prompts_res)}
        assert "triage_incident" in prompt_names

        rendered = await client.get_prompt(
            "triage_incident",
            {"service": "checkout", "symptom": "HTTP 500 errors"},
        )
        rendered_text = "\n".join(
            msg.content.text
            for msg in getattr(rendered, "messages", [])
            if hasattr(getattr(msg, "content", None), "text")
        )
        assert "checkout" in rendered_text
        assert "HTTP 500 errors" in rendered_text

        search_res = await client.call_tool("search_runbooks", {"query": "rollback"})
        search_text = "\n".join(
            item.text for item in getattr(search_res, "content", []) if hasattr(item, "text")
        )
        assert "git-rollback-guide" in search_text