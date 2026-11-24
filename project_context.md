### 1. Context & Teaching Approach

- **Role & Goal:** You are learning the **Model Context Protocol (MCP)** from scratch with me guiding and teaching you step by step—building a real, production-style project rather than isolated toy scripts.
- **Project Name:** `incident-triage-mcp` (paired with your completed `react-sql-analyst` / `sql-react-agent` project).
- **LLM Stack:** Using your **Groq API key** (`openai/gpt-oss-20b` via Groq's OpenAI-compatible endpoint using the `openai` Python SDK with a configurable `base_url`), paired with the official **MCP Python SDK (`mcp[cli]`)** and **Pydantic**.

### 2. What We Are Building (In Simple Terms)

An **automated incident triage and post-mortem system** that mimics what an on-call engineer does when a service breaks:

1. A service (such as a checkout/payment API) starts throwing errors.
2. You ask one question: *"Why is the service failing, and what should we do?"*
3. A central **Python MCP Client** (powered by your Groq LLM) connects to **3 separate MCP Servers** over standard MCP transports (`stdio` and `Streamable HTTP`):
   - **Ops / Telemetry Server (`ops-telemetry-mcp`):** Checks service health and tails error logs (with SSRF protection on HTTP probes).
   - **Git Forensics Server (`git-forensics-mcp`):** Inspects recent commits, diffs, and blame safely via `subprocess` (no shell injection).
   - **Runbook Knowledge Base Server (`runbook-kb-mcp`):** Reads Markdown troubleshooting runbooks, exposes prompt templates, and saves a post-mortem report only after **human-in-the-loop approval** and path-traversal checks.

### 3. Where We Are Right Now

- **Completed (`react-sql-analyst`):** Built and verified the ReAct SQL agent (14/14 unit tests passing, 75% eval pass rate with `eval_03` identified as a schema-round-trip / step-budget optimization opportunity).
- **Started (`incident-triage-mcp`):** Created the project folder, virtual environment (`venv`), and `.gitignore`; reviewed MCP core concepts (**Tools**, **Resources**, **Prompts**) and transports (**`stdio`** vs. **Streamable HTTP**); defined the initial directory structure and `pyproject.toml`.

### 4. Exact Step-by-Step Roadmap Ahead

1. **Environment & SDK Verification:** Install `mcp[cli]`, `httpx`, `openai`, `pydantic`, `pydantic-settings`, and `python-dotenv` in editable mode (`pip install -e ".[dev]"`) and verify the installed `mcp` version.
2. **Simulated Incident Workspace (Phase 1 Data Setup):** Create a local sample app/repo with a realistic bug commit in Git, sample error logs, and Markdown runbooks so our servers have real data to inspect.
3. **Server 1 — Telemetry & Logs (`Streamable HTTP`):** Build the first MCP server using `MCPServer` from `mcp.server`, expose resources and tools, and test it with the MCP Inspector (`mcp dev`).
4. **Server 2 — Git Forensics (`stdio`):** Build the Git inspection server over `stdio` (remembering `stdout` is for JSON-RPC, so logs go to `stderr`) with safe subprocess handling.
5. **Server 3 — Runbooks & Post-Mortems (`stdio`):** Add MCP Resources (`runbook://...`), MCP Prompts (slash-style triage templates), path-safe report writing, and human approval flow.
6. **Multi-Server Python MCP Client + Groq:** Connect a single Python MCP Client to all 3 servers at once, dynamically discover tools/resources/prompts, run end-to-end incident triage queries on Groq, and write tests/evals.

### Copy-Paste Starter Prompt for a New Chat

> *"Continue teaching me MCP from scratch on our `incident-triage-mcp` project using my Groq API key and the MCP Python SDK (`mcp[cli]`). We are building a 3-server incident triage system (Telemetry over Streamable HTTP, Git Forensics over stdio, and Runbooks/Post-Mortems over stdio with human approval) plus a Python MCP Client. Let's pick up from verifying `pip install -e ".[dev]"` and setting up the simulated broken service workspace."4*
