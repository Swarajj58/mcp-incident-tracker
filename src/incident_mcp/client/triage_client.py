from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from openai import AsyncOpenAI

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _extract_text_from_mcp_result(result: Any) -> str:
    """Extract readable text from an MCP tool or resource response."""
    if hasattr(result, "content") and result.content:
        parts: list[str] = []
        for item in result.content:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if hasattr(result, "contents") and result.contents:
        parts = []
        for item in result.contents:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "\n".join(parts)
    if hasattr(result, "structured_content") and result.structured_content is not None:
        return json.dumps(result.structured_content, indent=2)
    return str(result)


class IncidentTriageOrchestrator:
    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set in environment or .env")

        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.telemetry_url = os.getenv("TELEMETRY_MCP_URL", "http://127.0.0.1:8000/mcp")

        self.llm = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.exit_stack = AsyncExitStack()
        self.clients: dict[str, Client] = {}
        self.tool_routing: dict[str, tuple[str, str]] = {}
        self.openai_tools: list[dict[str, Any]] = []

    async def connect_all(self) -> None:
        """Connect to Telemetry (Streamable HTTP) plus Git and Runbook servers (stdio)."""
        stdio_specs = {
            "git": StdioServerParameters(
                command=sys.executable,
                args=["-m", "incident_mcp.servers.git_forensics_server"],
                cwd=str(PROJECT_ROOT),
            ),
            "runbook": StdioServerParameters(
                command=sys.executable,
                args=["-m", "incident_mcp.servers.runbook_server"],
                cwd=str(PROJECT_ROOT),
            ),
        }

        http_client = await self.exit_stack.enter_async_context(Client(self.telemetry_url))
        self.clients["telemetry"] = http_client

        for alias, params in stdio_specs.items():
            stdio_client = await self.exit_stack.enter_async_context(Client(params))
            self.clients[alias] = stdio_client

        await self._discover_tools()

    async def _discover_tools(self) -> None:
        self.tool_routing.clear()
        self.openai_tools.clear()

        for alias, client in self.clients.items():
            tools_response = await client.list_tools()
            tool_list = getattr(tools_response, "tools", tools_response)
            for tool in tool_list:
                namespaced_name = f"{alias}__{tool.name}"
                self.tool_routing[namespaced_name] = (alias, tool.name)
                self.openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": namespaced_name,
                            "description": f"[{alias}] {tool.description or ''}".strip(),
                            "parameters": tool.input_schema
                            or {"type": "object", "properties": {}},
                        },
                    }
                )

    async def gather_initial_context(self, service: str = "checkout") -> str:
        """Read initial MCP Resources across servers before starting the LLM loop."""
        sections: list[str] = []

        status_res = await self.clients["telemetry"].read_resource(f"service://{service}/status")
        sections.append(f"### Service Status Resource\n{_extract_text_from_mcp_result(status_res)}")

        commits_res = await self.clients["git"].read_resource("git://recent-commits")
        sections.append(f"### Recent Commits Resource\n{_extract_text_from_mcp_result(commits_res)}")

        runbooks_res = await self.clients["runbook"].read_resource("runbook://list")
        sections.append(f"### Available Runbooks Resource\n{_extract_text_from_mcp_result(runbooks_res)}")

        return "\n\n".join(sections)

    async def get_server_prompt(
            self, server_alias: str, prompt_name: str, arguments: dict[str, str]
        ) -> str:
            """Fetch and render an MCP Prompt template from a connected server."""
            prompt_res = await self.clients[server_alias].get_prompt(prompt_name, arguments)
            parts: list[str] = []
            for message in getattr(prompt_res, "messages", []):
                content = getattr(message, "content", None)
                if hasattr(content, "text"):
                    parts.append(content.text)
                elif isinstance(content, str):
                    parts.append(content)
                else:
                    parts.append(str(content))
            return "\n\n".join(parts)

    def _confirm_write_action(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Human-in-the-loop gate for write actions such as saving a post-mortem report."""
        print("\n[HUMAN APPROVAL REQUIRED]")
        print(f"Tool requested: {tool_name}")
        print(f"Arguments: {json.dumps(args, indent=2)[:800]}")
        choice = input("Approve executing this write tool? [y/N]: ").strip().lower()
        return choice in {"y", "yes"}

    async def run_triage(self, incident_prompt: str, max_steps: int = 8) -> str:
            context_block = await self.gather_initial_context("checkout")
            system_prompt = (
                "You are an incident triage assistant coordinating three MCP servers: "
                "telemetry (logs & endpoint health), git (commit history & diffs), and runbook "
                "(runbook search & saving post-mortem reports).\n"
                "Use the investigation tools to inspect logs, commits, and runbooks. "
                "Do NOT call save_postmortem_report via tool_calls; instead, write the complete, "
                "well-structured Markdown post-mortem report directly in your final text response "
                "including root cause, log/git evidence, and rollback/remediation steps."
            )

            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"{incident_prompt}\n\nInitial MCP Resource Snapshot:\n{context_block}",
                },
            ]

            for step in range(1, max_steps + 1):
                response = await self.llm.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.openai_tools,
                    tool_choice="auto",
                    temperature=0.2,
                )
                msg = response.choices[0].message
                tool_calls = msg.tool_calls or []

                assistant_entry: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content or "",
                }
                if tool_calls:
                    assistant_entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ]
                messages.append(assistant_entry)

                if not tool_calls:
                    report_text = (msg.content or "").strip()
                    if report_text and "runbook" in self.clients:
                        save_args = {
                            "incident_id": "inc-checkout-500",
                            "markdown_content": report_text,
                        }
                        if self._confirm_write_action("runbook__save_postmortem_report", save_args):
                            save_res = await self.clients["runbook"].call_tool(
                                "save_postmortem_report", save_args
                            )
                            save_status = _extract_text_from_mcp_result(save_res)
                            report_text = f"{report_text}\n\n---\n**Persistence Status:** {save_status}"
                        else:
                            report_text = (
                                f"{report_text}\n\n---\n"
                                "**Persistence Status:** Skipped (not approved by operator)."
                            )
                    return report_text or "Triage completed without final text output."

                for tc in tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments or "{}"
                    try:
                        parsed_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        parsed_args = {}

                    if fn_name not in self.tool_routing:
                        tool_output = f"Unknown tool: {fn_name}"
                    else:
                        server_alias, raw_tool_name = self.tool_routing[fn_name]
                        print(f"[Step {step}] Calling {fn_name} with {parsed_args}")
                        mcp_res = await self.clients[server_alias].call_tool(
                            raw_tool_name, parsed_args
                        )
                        tool_output = _extract_text_from_mcp_result(mcp_res)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tool_output,
                        }
                    )

            return "Reached max triage steps before producing a final response."

    async def close(self) -> None:
        await self.exit_stack.aclose()

async def main() -> None:
    orchestrator = IncidentTriageOrchestrator()
    try:
        await orchestrator.connect_all()
        prompt_instructions = await orchestrator.get_server_prompt(
            server_alias="runbook",
            prompt_name="triage_incident",
            arguments={
                "service": "checkout",
                "symptom": "HTTP 500 errors on /checkout requests",
            },
        )
        print("=== LOADED MCP PROMPT FROM runbook-kb-mcp ===\n")
        print(prompt_instructions)
        print("\n=============================================\n")

        final_report = await orchestrator.run_triage(prompt_instructions)
        print("\n=== FINAL TRIAGE SUMMARY ===\n")
        print(final_report)
    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())