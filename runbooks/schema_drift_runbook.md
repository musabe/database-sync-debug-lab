# Runbook: Sync Failure Due to Schema Drift

## Purpose

This runbook explains how to investigate and resolve sync failures caused by schema drift — when the source database schema changes (e.g. a column is added, renamed, or dropped) but the destination schema is not updated to match.

---

## Symptoms

A customer may report:

- Sync job fails with a database error referencing an unknown column
- New fields visible in the source are missing from destination records
- Sync was working correctly until a recent source schema change
- Error log contains messages such as:
  - `column "X" of relation "users" does not exist`
  - `INSERT has more expressions than target columns`

---

## Environment

- Source: PostgreSQL
- Destination: PostgreSQL
- Sync mode: incremental
- Conflict strategy: `ON CONFLICT (id) DO UPDATE`

---

## Root Cause

The sync script selects specific columns from the source (`id`, `name`, `email`, `updated_at`, `deleted_at`). If the source table gains a new column and the sync query is updated to include it, but the destination table is not altered to match, the destination `INSERT` will fail.

The reverse is also possible: a column dropped from the source but still referenced in the destination `INSERT` will cause the same class of error.

---

## Diagnosis

### 1. Check the sync error log

Look for the exact column name in the error message:

```
column "phone" of relation "users" does not exist
```

### 2. Compare source and destination schemas

Run on **sourcedb** (port 5433):

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

Run on **destdb** (port 5434):

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

Compare the two result sets. Any column present in one but absent from the other is the source of the drift.

### 3. Confirm the mismatch causes the failure

Run the failing INSERT manually on destdb:

```sql
INSERT INTO users (id, name, email, phone, updated_at)
VALUES (99, 'Test', 'test@test.com', '555-0100', NOW());
-- Expected: ERROR: column "phone" of relation "users" does not exist
```

---

## Resolution

### Option A — Add the missing column to the destination (recommended)

Apply a matching `ALTER TABLE` on destdb:

```sql
ALTER TABLE users ADD COLUMN phone TEXT;
```

For a non-nullable column with a default:

```sql
ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT '';
```

Re-run the sync. The cursor in `last_sync.txt` resumes from the last successful position so no rows are skipped.

### Option B — Exclude the column from the sync query

If the new source column should not be synced (e.g. it contains internal metadata), remove it from the `SELECT` in `sync.py` and the destination `INSERT`. The destination schema stays unchanged.

---

## Prevention

1. **Treat destination schema changes as part of source migrations** — whenever a column is added to the source, include a corresponding `ALTER TABLE` for the destination in the same migration or deployment step.

2. **Add a schema check to sync startup** — query `information_schema.columns` on both databases at the start of each run and fail fast with a clear error if the column sets diverge, before any rows are processed.

3. **Test schema changes against the destination in CI** — include both Docker containers in your CI pipeline so integration tests catch drift before it reaches production.

---

## Related

- `scenarios/schema_drift.md` — reproduction steps
- `sql/broken_scenarios.sql` — Scenario 3: SQL that demonstrates the failure and fix
- `sql/source_schema.sql` / `sql/destination_schema.sql` — current table definitions
