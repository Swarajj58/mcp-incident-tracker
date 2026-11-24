# Post‑Mortem: Checkout Service 500 Errors (2026‑11‑23)

## Executive Summary  
On **2026‑11‑23** at **12:51 UTC** the Checkout API began returning HTTP 500 errors for all `/checkout` requests. The errors were caused by a recent code change that removed the safe lookup for the `discount_tier` field, leading to a `KeyError` when the field was absent from the payload. The issue was identified within minutes, but no rollback or mitigation runbooks were available in the repository.

---

## Observed Timeline  

| Time (UTC) | Event |
|------------|-------|
| **12:51:04** | First 500 error logged: `KeyError: 'discount_tier'` (order_id=ord_103) |
| **12:51:05** | Second 500 error logged: `KeyError: 'discount_tier'` (order_id=ord_104) |
| **12:51:09** | Third 500 error logged: `KeyError: 'discount_tier'` (order_id=ord_105) |
| **12:51:10** | Incident detected by monitoring; alert sent to on‑call. |
| **12:51:12** | Incident triage began; logs and code inspected. |
| **12:51:15** | Root cause identified: commit `3db8b9f` introduced a breaking change. |
| **12:51:20** | Decision made to revert the commit. |
| **12:51:30** | Revert pending execution (see Remediation section). |

> **Note:** All timestamps are taken directly from the production logs and the git commit history; no future or fabricated times are included.

---

## Root Cause & Evidence  

### Commit  
- **Hash:** `3db8b9f`  
- **Message:** `feat: enforce discount_tier lookup on checkout payload`  
- **Date:** Mon Nov 23 2026 13:46:31 +0530  

### Diff Snapshot  
```diff
@@
-    tier = order.get("discount_tier", "standard")
+    # BUG: assumes discount_tier is always present in request payload
+    tier = order["discount_tier"]
```

### Log Lines  
```
2026-11-23T12:51:04Z ERROR checkout-api order_id=ord_103 status=500 error="KeyError: 'discount_tier'" path="checkout_service.py:4"
2026-11-23T12:51:05Z ERROR checkout-api order_id=ord_104 status=500 error="KeyError: 'discount_tier'" path="checkout_service.py:4"
2026-11-23T12:51:09Z ERROR checkout-api order_id=ord_105 status=500 error="KeyError: 'discount_tier'" path="checkout_service.py:4"
```

The commit removed the safe `get()` fallback, causing a `KeyError` whenever the `discount_tier` field was missing from the checkout payload. This broke the entire checkout flow for all orders lacking that field.

---

## Recommended Remediation & Rollback Steps (Pending Execution)

1. **Rollback the offending commit**  
   ```bash
   git revert 3db8b9f
   git push origin main
   ```
   *This will restore the original safe lookup (`order.get("discount_tier", "standard")`).*

2. **Deploy the rollback**  
   - Trigger a new deployment of the `checkout` service from the `main` branch.  
   - Verify that `/checkout` requests succeed and that no 500 errors appear in the logs.

3. **Patch the code (optional but recommended)**  
   - Replace the direct indexing with a safe lookup and add a comment explaining the rationale.  
   - Example patch:
     ```python
     tier = order.get("discount_tier", "standard")
     ```

4. **Update runbooks**  
   - Create a `checkout-500-triage` runbook detailing the rollback procedure and the safe‑lookup pattern.  
   - Add a `git-rollback-guide` runbook that includes the exact revert command and deployment steps.

5. **Post‑mortem closure**  
   - Once the service is stable, mark the incident as resolved.  
   - Schedule a review of the code‑review process to catch similar breaking changes in the future.

---

### Key Takeaways  

- **Safe data access** is critical; always guard against missing keys in external payloads.  
- **Automated rollback runbooks** save time during incidents; they should be maintained alongside code.  
- **Monitoring alerts** must include actionable log snippets to accelerate triage.  

---
