-- seed_data.sql
--
-- Inserts two test users into the source database so there is something to sync.
-- This runs once when the source container starts up.
-- Alice and Bob are the baseline records used across all scenarios and tests.
INSERT INTO users (name, email)
VALUES
('Alice', 'alice@test.com'),
('Bob', 'bob@test.com');