# Runbook: Missing Records Due to Timestamp Collision

## Symptoms

- Some records missing in destination
- No errors during sync
- Data mismatch between source and destination
- Issue appears intermittently

---

## Root Cause

Incremental sync uses:

```sql
WHERE updated_at > last_sync_time