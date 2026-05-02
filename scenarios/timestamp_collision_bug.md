# Timestamp Collision Bug

## Problem

Incremental sync uses:

WHERE updated_at > last_sync

If multiple rows share the same updated_at timestamp, rows may be skipped.

## Reproduction

1. Insert multiple rows with identical timestamps
2. Run sync
3. Update last_sync
4. Some rows may not be processed

## Root Cause

Using strict > instead of >= and no secondary ordering key

## Fix Strategy

Use:
- >= comparison
- AND (id > last_id) tie-breaker