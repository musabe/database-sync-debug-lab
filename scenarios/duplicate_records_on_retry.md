# Duplicate Records on Retry Scenario

## Scenario

The sync process is retried after a partial failure. Because the destination table does not handle updates correctly, repeated sync attempts can create inconsistent destination data or fail to reflect source changes.

## Goal

Reproduce and investigate a common data integration issue:

- source record changes
- sync runs again
- destination does not update existing row
- data becomes stale

## Expected Behavior

If a source row changes, the destination row should be updated.

## Current Behavior

The script uses:

```sql
ON CONFLICT (id) DO NOTHING
