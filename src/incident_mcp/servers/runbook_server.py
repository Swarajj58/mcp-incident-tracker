from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from mcp.server import MCPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [runbook-kb] %(message)s")
logger = logging.getLogger("runbook-kb-mcp")

RUNBOOKS_DIR = Path(os.getenv("INCIDENT_RUNBOOKS_DIR", "demo_workspace/runbooks")).resolve()
POSTMORTEMS_DIR = Path(
    os.getenv("INCIDENT_POSTMORTEMS_DIR", "demo_workspace/postmortems")
).resolve()

SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")

mcp = MCPServer("runbook-kb-mcp")


def _resolve_runbook(slug: str) -> Path:
    if not SLUG_RE.match(slug):
        raise ValueError("Invalid runbook slug; use only letters, numbers, hyphens, or underscores.")
    RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    target = (RUNBOOKS_DIR / f"{slug}.md").resolve()
    if RUNBOOKS_DIR not in target.parents:
        raise ValueError("Path escapes runbooks directory.")
    if not target.exists():
        raise FileNotFoundError(f"Runbook not found for slug: {slug}")
    return target


def _resolve_postmortem_path(incident_id: str) -> Path:
    if not SLUG_RE.match(incident_id):
        raise ValueError("Invalid incident_id; use only letters, numbers, hyphens, or underscores.")
    POSTMORTEMS_DIR.mkdir(parents=True, exist_ok=True)
    target = (POSTMORTEMS_DIR / f"{incident_id}.md").resolve()
    if POSTMORTEMS_DIR not in target.parents:
        raise ValueError("Path escapes postmortems directory.")
    return target


@mcp.resource("runbook://list")
def list_runbooks() -> str:
    """List available Markdown runbook slugs."""
    logger.info("Listing runbooks from %s", RUNBOOKS_DIR)
    if not RUNBOOKS_DIR.exists():
        return "No runbooks directory found."
    slugs = sorted(p.stem for p in RUNBOOKS_DIR.glob("*.md"))
    if not slugs:
        return "No runbooks available."
    return "\n".join(f"- {slug}" for slug in slugs)


@mcp.resource("runbook://read/{slug}")
def read_runbook(slug: str) -> str:
    """Read the full Markdown content of a specific runbook by slug."""
    logger.info("Reading runbook '%s'", slug)
    path = _resolve_runbook(slug)
    return path.read_text(encoding="utf-8")


@mcp.tool()
def search_runbooks(query: str) -> str:
    """Search across all Markdown runbooks for lines matching a keyword or phrase."""
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("Search query cannot be empty.")
    if not RUNBOOKS_DIR.exists():
        return "No runbooks directory found."

    needle = cleaned.lower()
    matches: list[str] = []
    for path in sorted(RUNBOOKS_DIR.glob("*.md")):
        for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if needle in line.lower():
                matches.append(f"[{path.stem}:{idx}] {line.strip()}")

    if not matches:
        return f"No runbook matches found for {cleaned!r}."
    return "\n".join(matches[:50])


@mcp.tool()
def save_postmortem_report(incident_id: str, markdown_content: str) -> str:
    """Save a formatted Markdown post-mortem report for an incident."""
    if not markdown_content.strip():
        raise ValueError("markdown_content cannot be empty.")
    target = _resolve_postmortem_path(incident_id)
    target.write_text(markdown_content.strip() + "\n", encoding="utf-8")
    logger.info("Saved post-mortem report to %s", target)
    return f"Saved post-mortem report to {target}"


@mcp.prompt()
def triage_incident(service: str, symptom: str) -> str:
    """Generate a structured incident triage instruction prompt for a failing service."""
    return (
        f"Investigate a production incident on service '{service}' with symptom: {symptom}.\n"
        "Follow these steps:\n"
        "1. Tail recent ERROR/5xx logs using telemetry tools to identify exact timestamps, error messages, and file paths.\n"
        "2. Inspect recent Git commits and diffs in the repository to pinpoint the breaking change.\n"
        "3. Search runbooks for matching triage and rollback procedures.\n"
        "4. Write a concise Markdown post-mortem report containing:\n"
        "   - Executive Summary\n"
        "   - Observed Timeline (STRICTLY use only timestamps present in logs/git; never invent future rollback or closure times)\n"
        "   - Root Cause & Evidence (exact commit hash, diff, and log lines)\n"
        "   - Recommended Remediation & Rollback Steps (clearly labeled as pending execution)\n"
    )

if __name__ == "__main__":
    mcp.run()