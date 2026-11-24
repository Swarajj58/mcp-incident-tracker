from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path

from mcp.server import MCPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [git-forensics] %(message)s")
logger = logging.getLogger("git-forensics-mcp")

DEFAULT_REPO_DIR = Path(os.getenv("INCIDENT_REPO_DIR", "demo_workspace/app")).resolve()
COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")

mcp = MCPServer("git-forensics-mcp")


def _ensure_git_repo() -> Path:
    repo = DEFAULT_REPO_DIR
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"Not a valid Git repository: {repo}")
    return repo


def _run_git(args: list[str]) -> str:
    repo = _ensure_git_repo()
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        shell=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _resolve_repo_file(rel_path: str) -> str:
    repo = _ensure_git_repo()
    candidate = (repo / rel_path).resolve()
    if repo not in candidate.parents:
        raise ValueError("File path escapes the repository root.")
    if not candidate.exists():
        raise FileNotFoundError(f"File does not exist in repo: {rel_path}")
    return candidate.relative_to(repo).as_posix()


@mcp.resource("git://recent-commits")
def recent_commits_resource() -> str:
    """List the 10 most recent commits in the target repository."""
    logger.info("Reading git://recent-commits resource")
    return _run_git(["log", "-n", "10", "--oneline"])


@mcp.tool()
def get_commit_diff(commit_hash: str) -> str:
    """Show commit metadata and unified diff for a specific commit hash."""
    cleaned = commit_hash.strip()
    if not COMMIT_HASH_RE.match(cleaned):
        raise ValueError("Invalid commit_hash format; expected 7-40 hex characters.")
    logger.info("Inspecting commit diff for %s", cleaned)
    return _run_git(["show", "--stat", "--patch", cleaned])


@mcp.tool()
def get_file_blame(file_path: str, line_start: int = 1, line_end: int = 50) -> str:
    """Show git blame annotations for a line range in a repository file."""
    if line_start < 1 or line_end < line_start:
        raise ValueError("Invalid line range: require 1 <= line_start <= line_end.")
    if (line_end - line_start) > 200:
        raise ValueError("Line range too wide; request at most 200 lines at a time.")

    safe_rel = _resolve_repo_file(file_path)
    logger.info("Running git blame on %s:%d-%d", safe_rel, line_start, line_end)
    return _run_git(["blame", "-L", f"{line_start},{line_end}", safe_rel])


if __name__ == "__main__":
    mcp.run()