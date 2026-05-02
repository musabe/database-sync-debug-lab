-- broken_scenarios.sql
--
-- Contains SQL queries that reproduce known bugs and failure cases in the sync pipeline.
-- Run these manually against a live database to trigger and observe a specific problem
-- without having to run the full sync script.
--
-- Each scenario is self-contained. Read the header comment before running a block —
-- some blocks deliberately break things so you can observe the failure.
-- Cleanup queries are provided at the end of each scenario.


-- =============================================================================
-- SCENARIO 1: Timestamp Collision Bug (run against sourcedb)
--
-- A naive incremental query uses strict `updated_at > :last_sync`.
-- When multiple rows share the same timestamp, all but the first are silently
-- skipped on the next run because the cursor advances past them.
-- =============================================================================

-- Setup: insert three rows all sharing the same updated_at.
INSERT INTO users (name, email, updated_at) VALUES
    ('Carol', 'carol@test.com', '2024-01-01 10:00:00'),
    ('Dave',  'dave@test.com',  '2024-01-01 10:00:00'),
    ('Eve',   'eve@test.com',   '2024-01-01 10:00:00');

-- Suppose sync ran and saved cursor = 2024-01-01T10:00:00 after processing Carol (id=3).

-- BROKEN query — strict > misses Dave and Eve entirely.
-- Expected: 2 rows. Actual: 0 rows.
SELECT id, name, updated_at
FROM users
WHERE updated_at > '2024-01-01 10:00:00'
ORDER BY updated_at, id;

-- FIXED query — compound cursor picks up ties at the same timestamp.
-- Replace 3 with the actual last synced id from last_sync.txt.
SELECT id, name, updated_at
FROM users
WHERE
    updated_at > '2024-01-01 10:00:00'
    OR (updated_at = '2024-01-01 10:00:00' AND id > 3)
ORDER BY updated_at, id;

-- Cleanup
DELETE FROM users WHERE name IN ('Carol', 'Dave', 'Eve');


-- =============================================================================
-- SCENARIO 2: Stale Destination Record — DO NOTHING Bug (run against destdb)
--
-- When the upsert uses ON CONFLICT DO NOTHING, a changed source row is silently
-- ignored on retry. The destination keeps the old value indefinitely.
-- =============================================================================

-- Setup: Alice exists in destination with her original email.
INSERT INTO users (id, name, email, updated_at)
VALUES (1, 'Alice', 'alice@test.com', '2024-01-01 10:00:00');

-- Alice changes her email in the source. Sync re-runs with the updated row.

-- BROKEN upsert — conflict is ignored, stale email survives.
INSERT INTO users (id, name, email, updated_at)
VALUES (1, 'Alice', 'alice@newdomain.com', '2024-06-01 09:00:00')
ON CONFLICT (id) DO NOTHING;

-- Observe: email is still alice@test.com, not alice@newdomain.com.
SELECT id, email FROM users WHERE id = 1;

-- FIXED upsert — conflict overwrites all columns with fresh source data.
INSERT INTO users (id, name, email, updated_at)
VALUES (1, 'Alice', 'alice@newdomain.com', '2024-06-01 09:00:00')
ON CONFLICT (id) DO UPDATE
    SET name       = EXCLUDED.name,
        email      = EXCLUDED.email,
        updated_at = EXCLUDED.updated_at;

-- Observe: email is now alice@newdomain.com.
SELECT id, email FROM users WHERE id = 1;

-- Cleanup
DELETE FROM users WHERE id = 1;


-- =============================================================================
-- SCENARIO 3: Schema Drift (run step 1-2 against sourcedb, step 3 against destdb)
--
-- A new column is added to the source table but not the destination.
-- Any INSERT that references the new column will fail on the destination,
-- halting the sync entirely.
-- =============================================================================

-- Step 1 (sourcedb): add a new column to the source.
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT;

-- Step 2 (sourcedb): insert a row that uses the new column.
INSERT INTO users (name, email, phone, updated_at)
VALUES ('Frank', 'frank@test.com', '555-0100', NOW());

-- Step 3 (destdb): attempt to mirror the row — fails because destination
-- has no phone column.
-- ERROR: column "phone" of relation "users" does not exist
INSERT INTO users (id, name, email, phone, updated_at)
VALUES (10, 'Frank', 'frank@test.com', '555-0100', NOW());

-- Cleanup (sourcedb)
ALTER TABLE users DROP COLUMN IF EXISTS phone;
DELETE FROM users WHERE name = 'Frank';


-- =============================================================================
-- SCENARIO 4: Missing Index on updated_at (run against sourcedb)
--
-- Without an index on (updated_at, id), every sync run performs a full table
-- scan regardless of how many rows are actually new. EXPLAIN reveals this.
-- =============================================================================

-- Observe: Seq Scan — every row is examined on every sync run.
EXPLAIN
SELECT id, name, email, updated_at
FROM users
WHERE
    updated_at > '2024-01-01 10:00:00'
    OR (updated_at = '2024-01-01 10:00:00' AND id > 0)
ORDER BY updated_at, id;

-- Fix: composite index covers both columns used in the compound cursor query.
CREATE INDEX IF NOT EXISTS idx_users_updated_at_id ON users (updated_at, id);

-- Observe: Index Scan replaces Seq Scan.
EXPLAIN
SELECT id, name, email, updated_at
FROM users
WHERE
    updated_at > '2024-01-01 10:00:00'
    OR (updated_at = '2024-01-01 10:00:00' AND id > 0)
ORDER BY updated_at, id;

-- Cleanup (the index is a net improvement — remove only if testing without it)
-- DROP INDEX IF EXISTS idx_users_updated_at_id;


-- =============================================================================
-- SCENARIO 5: Permissions Error (run against sourcedb as a superuser)
--
-- If the sync user loses SELECT privilege — e.g. after a migration that
-- recreates the table — every sync run fails immediately with
-- "permission denied for table users".
-- =============================================================================

-- Step 1: revoke read access from the sync user.
REVOKE SELECT ON users FROM demo;

-- Step 2: sync query now fails.
-- ERROR: permission denied for table users
SELECT id, name, email, updated_at
FROM users
WHERE updated_at > '1970-01-01 00:00:00'
ORDER BY updated_at, id;

-- Fix: restore the privilege.
GRANT SELECT ON users TO demo;
