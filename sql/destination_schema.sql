-- destination_schema.sql
--
-- Creates the users table in the destination database (destdb, port 5434).
-- This is where the sync script writes data to. The structure mirrors the source
-- table so records can be copied across without any transformation.
-- id uses plain INT instead of SERIAL because the values come from the source —
-- the destination never generates its own IDs.
CREATE TABLE users (
    id INT PRIMARY KEY,
    name TEXT,
    email TEXT,
    updated_at TIMESTAMP
);