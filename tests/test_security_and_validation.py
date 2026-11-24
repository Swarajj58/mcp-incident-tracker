from __future__ import annotations

import pytest

from incident_mcp.servers import git_forensics_server, runbook_server, telemetry_server


def test_ssrf_blocks_localhost_and_private_ips() -> None:
    blocked_urls = [
        "http://localhost:8000/admin",
        "http://127.0.0.1:8000/metrics",
        "http://10.0.0.5/internal",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file.txt",
    ]
    for url in blocked_urls:
        allowed, reason = telemetry_server._is_safe_public_url(url)
        assert not allowed, f"Expected URL to be blocked: {url}"
        assert reason


def test_telemetry_rejects_path_traversal_service_name() -> None:
    with pytest.raises(ValueError):
        telemetry_server._resolve_log_file("../secrets")


def test_runbook_blocks_path_traversal_and_bad_slugs() -> None:
    with pytest.raises(ValueError):
        runbook_server._resolve_runbook("../outside")

    with pytest.raises(ValueError):
        runbook_server._resolve_postmortem_path("../../etc/passwd")

    with pytest.raises(ValueError):
        runbook_server.save_postmortem_report("inc-valid-id", "   ")


def test_git_forensics_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        git_forensics_server.get_commit_diff("not-a-valid-hash; rm -rf /")

    with pytest.raises(ValueError):
        git_forensics_server.get_file_blame("checkout_service.py", line_start=10, line_end=5)

    with pytest.raises(ValueError):
        git_forensics_server._resolve_repo_file("../checkout.log")