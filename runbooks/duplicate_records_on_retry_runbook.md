# Runbook: Duplicate / Stale Records After Retry

## Purpose

This runbook explains how to investigate cases where a database sync appears successful but destination records are duplicated, stale, or inconsistent after a retry.

---

## Symptoms

A customer may report:

- Destination data does not match source data
- Sync job completes successfully but old values remain
- Re-running the sync does not fix the issue
- Updated records are not reflected in the destination database

---

## Environment

- Source: PostgreSQL
- Destination: PostgreSQL
- Sync mode: incremental
- Cursor column: `updated_at`
- Conflict strategy: `ON CONFLICT DO NOTHING`

---

## Initial Checks

### 1. Confirm source value

```sql
SELECT id, name, email, updated_at
FROM users
WHERE id = 1;