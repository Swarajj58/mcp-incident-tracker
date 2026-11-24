# Checkout API 500 Error Triage Runbook

## Symptoms
- HTTP 500 responses on `/checkout`
- `KeyError` exceptions in `checkout.log`

## Investigation Steps
1. Tail recent ERROR lines in `checkout.log`.
2. Identify the failing file, line number, and exception.
3. Inspect recent Git commits and diffs.
4. Look for unguarded dictionary key lookups.
5. Prepare a rollback plan and document the incident.
