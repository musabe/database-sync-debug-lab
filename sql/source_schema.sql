-- source_schema.sql
--
-- Creates the users table in the source database (sourcedb, port 5433).
-- This is where all original data lives. The sync script reads from this table
-- and copies records over to the destination.
-- The updated_at column is automatically set to the current time on insert,
-- which is what the sync script uses to detect new or changed rows.
-- deleted_at is NULL for live rows. Setting it (alongside bumping updated_at)
-- signals to the sync script that the row should be removed from the destination.
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP NULL DEFAULT NULL
);