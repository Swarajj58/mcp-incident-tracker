================================================================================
MCP STUDY ROADMAP — SEQUENCE, STATUS & IMPORTANCE
================================================================================

PART 1: TOPICS COVERED (IN BUILD SEQUENCE)
--------------------------------------------------------------------------------
1. MCP Architecture & Transports (stdio vs. Streamable HTTP)
   - Status: COVERED
   - What you did: Ran git-forensics-mcp and runbook-kb-mcp over stdio; ran
     ops-telemetry-mcp over Streamable HTTP (http://127.0.0.1:8000/mcp).
   - Importance: CRITICAL — Determines how clients connect to local child
     processes versus remote/shared network services, and how stdout/stderr
     logging must be separated so JSON-RPC streams are not corrupted.

2. MCP Tools (@mcp.tool(), Dynamic Discovery & Namespaced Routing)
   - Status: COVERED
   - What you did: Built tail_error_logs, probe_endpoint, get_commit_diff,
     get_file_blame, search_runbooks, and save_postmortem_report; discovered
     schemas at runtime and routed calls as server__tool.
   - Importance: CRITICAL — Tools are how models take actions and query live
     systems. Namespacing prevents collisions when connecting multiple servers.

3. MCP Resources (@mcp.resource() & URI Templates)
   - Status: COVERED
   - What you did: Exposed service://{service}/status, git://recent-commits,
     runbook://list, and runbook://read/{slug} to preload read-only context.
   - Importance: HIGH — Lets the host/client supply structured, read-only
     state or domain data without forcing the model to guess paths or spend
     extra tool-calling turns on baseline context.

4. MCP Prompts (@mcp.prompt() & Dynamic Rendering)
   - Status: COVERED
   - What you did: Defined triage_incident(service, symptom) on the runbook
     server and fetched/rendered it in triage_client.py.
   - Importance: MEDIUM-HIGH — Centralizes repeatable investigation and workflow
     instructions on the server so multiple clients share a consistent playbook.

5. Server-Side Security & Input Guardrails
   - Status: COVERED
   - What you did: Added SSRF IP/hostname filtering, path-traversal checks
     with Path.resolve(), slug/commit-hash regex validation, and safe
     subprocess argument lists (shell=False).
   - Importance: CRITICAL — Any tool taking URLs, file paths, or shell/git
     parameters is an attack surface for prompt-injected or malformed inputs.

6. Human-in-the-Loop (HITL) & Client-Side Persistence
   - Status: COVERED
   - What you did: Gated post-mortem file writes behind terminal [y/N]
     approval and moved long Markdown generation out of JSON tool arguments.
   - Importance: HIGH — Prevents unreviewed state mutations/writes and avoids
     LLM JSON-escaping failures on large text payloads.

7. Automated Testing with pytest (Unit + MCP Client Integration)
   - Status: COVERED
   - What you did: Wrote tests for security guardrails and async MCP client
     discovery, resource reads, prompt rendering, and tool calls (6/6 passing).
   - Importance: HIGH — Keeps protocol contracts, tool schemas, and security
     boundaries from regressing as servers and dependencies evolve.


PART 2: TOPICS NOT COVERED YET (RECOMMENDED LATER STUDY SEQUENCE)
--------------------------------------------------------------------------------
8. Ephemeral HTTP Test Fixtures & Full End-to-End Integration Tests
   - Status: NOT COVERED
   - What to study: Spinning up Streamable HTTP servers on dynamic ports inside
     pytest fixtures and testing full multi-server client flows automatically.
   - Importance: HIGH — Ensures network transport behavior, connection
     lifecycle, and error responses are verified in CI without manual servers.

9. Authentication, Authorization & Multi-Tenant Access Control
   - Status: NOT COVERED
   - What to study: OAuth 2.1 / JWT bearer token validation, per-tool scopes
     (read vs. write/rollback), and tenant isolation on HTTP MCP servers.
   - Importance: CRITICAL (for production) — Essential whenever remote MCP
     servers serve multiple users, teams, or external clients.

10. Real Enterprise Connectors, Pagination & Context Truncation
    - Status: NOT COVERED
    - What to study: Integrating live APIs (logs, metrics, Git hosts, issue
      trackers, wikis) with strict result limits, pagination, and token budgets.
    - Importance: HIGH — Real logs and diffs can easily overflow context
      windows or spike API/token costs if returned unbounded.

11. Advanced MCP Primitives: Elicitation, Sampling & Tasks
    - Status: NOT COVERED
    - What to study: Server-requested structured user input (elicitation),
      server-initiated LLM completions via client (sampling), and long-running
      async jobs with status polling (tasks).
    - Importance: MEDIUM-HIGH — Needed for interactive workflows, dynamic
      clarifications, and slow operations that exceed request timeouts.

12. Dynamic Capability Notifications & Tool Poisoning Defense
    - Status: NOT COVERED
    - What to study: Handling list_changed notifications when tools/resources
      update dynamically, and verifying tool descriptions/integrity when
      consuming third-party or untrusted MCP servers.
    - Importance: MEDIUM-HIGH — Protects against stale client tool caches and
      prompt-injection instructions hidden inside untrusted tool metadata.

13. Production Deployment, Sandboxing & Observability
    - Status: NOT COVERED
    - What to study: Containerizing MCP servers, isolating execution sandboxes,
      rate limiting, structured JSON logging, and OpenTelemetry tracing.
    - Importance: HIGH (for production) — Required to debug latency/failures
      across multi-server chains and contain blast radius in production.
================================================================================