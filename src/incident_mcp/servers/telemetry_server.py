from __future__ import annotations

import ipaddress
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import httpx
from mcp.server import MCPServer

DEFAULT_LOGS_DIR = Path(os.getenv("INCIDENT_LOGS_DIR", "demo_workspace/logs")).resolve()

mcp = MCPServer("ops-telemetry-mcp")


def _resolve_log_file(service: str) -> Path:
    """Resolve `<service>.log` safely inside `DEFAULT_LOGS_DIR`."""
    safe_name = Path(service).name
    if safe_name != service or not safe_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError(f"Invalid service name: {service!r}")
    log_path = (DEFAULT_LOGS_DIR / f"{safe_name}.log").resolve()
    if DEFAULT_LOGS_DIR not in log_path.parents:
        raise ValueError("Path escapes allowed logs directory.")
    return log_path


def _is_safe_public_url(url: str) -> tuple[bool, str]:
    """Basic SSRF check: allow only http/https and block private/loopback/link-local hosts."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False, "Only http and https URLs with a valid hostname are allowed."

    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".local"):
        return False, f"Blocked local/internal hostname: {host}"

    try:
        addr_info = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return False, f"Could not resolve hostname {host!r}: {exc}"

    for _, _, _, _, sockaddr in addr_info:
        ip_str = sockaddr[0]
        ip_obj = ipaddress.ip_address(ip_str)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return False, f"Blocked non-public IP address {ip_str} for host {host!r}."

    return True, "OK"


@mcp.resource("service://{service}/status")
def get_service_status(service: str) -> str:
    """Return a quick health and error summary for a service from its log file."""
    log_path = _resolve_log_file(service)
    if not log_path.exists():
        return f"Service '{service}': no log file found at {log_path}."

    lines = log_path.read_text(encoding="utf-8").splitlines()
    error_lines = [line for line in lines if "ERROR" in line or "status=5" in line]
    state = "DEGRADED" if error_lines else "HEALTHY"
    return (
        f"Service: {service}\n"
        f"Status: {state}\n"
        f"Total Log Lines: {len(lines)}\n"
        f"Error / 5xx Count: {len(error_lines)}"
    )


@mcp.tool()
def tail_error_logs(service: str, lines: int = 20, errors_only: bool = True) -> str:
    """Read recent log lines (defaulting to ERROR/5xx lines) for a given service."""
    if lines < 1 or lines > 200:
        raise ValueError("lines must be between 1 and 200.")

    log_path = _resolve_log_file(service)
    if not log_path.exists():
        return f"No log file found for service '{service}'."

    all_lines = log_path.read_text(encoding="utf-8").splitlines()
    filtered = (
        [line for line in all_lines if "ERROR" in line or "status=5" in line]
        if errors_only
        else all_lines
    )
    selected = filtered[-lines:]
    if not selected:
        return f"No matching log entries found for service '{service}'."
    return "\n".join(selected)


@mcp.tool()
async def probe_endpoint(url: str, timeout_seconds: float = 5.0) -> str:
    """Check HTTP status code and response latency for a public URL (SSRF-guarded)."""
    allowed, reason = _is_safe_public_url(url)
    if not allowed:
        return f"Blocked probe: {reason}"

    if timeout_seconds <= 0 or timeout_seconds > 15:
        raise ValueError("timeout_seconds must be between 0 and 15.")

    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=False) as client:
        response = await client.get(url)
        return (
            f"URL: {url}\n"
            f"Status Code: {response.status_code}\n"
            f"Latency (ms): {response.elapsed.total_seconds() * 1000:.1f}"
        )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", json_response=True)