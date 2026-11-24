
"""
To create files 

"""


from pathlib import Path
import subprocess

ROOT = Path("demo_workspace")
APP_DIR = ROOT / "app"
LOGS_DIR = ROOT / "logs"
RUNBOOKS_DIR = ROOT / "runbooks"
POSTMORTEMS_DIR = ROOT / "postmortems"

# Create workspace directories
for directory in (APP_DIR, LOGS_DIR, RUNBOOKS_DIR, POSTMORTEMS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


def run_git(*args: str) -> None:
    """Execute Git safely without invoking a shell."""
    subprocess.run(
        ["git", *args],
        cwd=APP_DIR,
        check=True,
    )


# 1. Create the baseline checkout service
service_file = APP_DIR / "checkout_service.py"

baseline_code = '''def calculate_total(order: dict) -> float:
    base_amount = float(order["amount"])
    tier = order.get("discount_tier", "standard")
    discount_map = {"standard": 0.0, "silver": 0.05, "gold": 0.10}
    discount = discount_map.get(tier, 0.0)
    return round(base_amount * (1.0 - discount), 2)
'''

service_file.write_text(baseline_code, encoding="utf-8")

# Initialize Git
run_git("init")
run_git("config", "user.name", "OnCall Engineer")
run_git("config", "user.email", "oncall@example.internal")

run_git("add", ".")
run_git("commit", "-m", "feat: add baseline checkout total calculation")

# 2. Introduce a deliberate regression
broken_code = '''def calculate_total(order: dict) -> float:
    base_amount = float(order["amount"])
    # BUG: assumes discount_tier is always present in request payload
    tier = order["discount_tier"]
    discount_map = {"standard": 0.0, "silver": 0.05, "gold": 0.10}
    discount = discount_map.get(tier, 0.0)
    return round(base_amount * (1.0 - discount), 2)
'''

service_file.write_text(broken_code, encoding="utf-8")

run_git("add", ".")
run_git(
    "commit",
    "-m",
    "feat: enforce discount_tier lookup on checkout payload",
)

# 3. Create simulated incident logs
log_content = """2026-11-23T12:40:02Z INFO checkout-api order_id=ord_101 status=200 latency_ms=42
2026-11-23T12:45:19Z INFO checkout-api order_id=ord_102 status=200 latency_ms=39
2026-11-23T12:51:04Z ERROR checkout-api order_id=ord_103 status=500 error="KeyError: 'discount_tier'" path="checkout_service.py:4"
2026-11-23T12:51:05Z ERROR checkout-api order_id=ord_104 status=500 error="KeyError: 'discount_tier'" path="checkout_service.py:4"
2026-11-23T12:51:09Z ERROR checkout-api order_id=ord_105 status=500 error="KeyError: 'discount_tier'" path="checkout_service.py:4"
"""

(LOGS_DIR / "checkout.log").write_text(
    log_content,
    encoding="utf-8",
)

# 4. Create runbooks
checkout_runbook = """# Checkout API 500 Error Triage Runbook

## Symptoms
- HTTP 500 responses on `/checkout`
- `KeyError` exceptions in `checkout.log`

## Investigation Steps
1. Tail recent ERROR lines in `checkout.log`.
2. Identify the failing file, line number, and exception.
3. Inspect recent Git commits and diffs.
4. Look for unguarded dictionary key lookups.
5. Prepare a rollback plan and document the incident.
"""

rollback_runbook = """# Safe Git Rollback Guide

- Always inspect `git log -n 5` and `git show <commit_hash>` before reverting.
- Prefer `git revert <commit_hash>` over `git reset --hard` on shared branches.
- Include root cause, affected orders, and rollback verification steps in the post-mortem.
"""

(RUNBOOKS_DIR / "checkout-500-triage.md").write_text(
    checkout_runbook,
    encoding="utf-8",
)

(RUNBOOKS_DIR / "git-rollback-guide.md").write_text(
    rollback_runbook,
    encoding="utf-8",
)

print("Workspace created successfully.")
print(f"Git repository: {APP_DIR.resolve()}")
print(f"Logs directory: {LOGS_DIR.resolve()}")
print(f"Runbooks directory: {RUNBOOKS_DIR.resolve()}")
