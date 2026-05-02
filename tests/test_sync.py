# Unit tests for sync logic.
# Tests cover cursor state read/write, incremental query correctness,
# upsert behaviour on conflict, and compound cursor advancement.
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import sync


# ---------------------------------------------------------------------------
# Cursor state — no DB required
# ---------------------------------------------------------------------------

def test_get_last_sync_state_missing_file(tmp_path):
    with patch.object(sync, "STATE_FILE", str(tmp_path / "state.txt")):
        ts, last_id = sync.get_last_sync_state()
    assert ts == datetime(1970, 1, 1)
    assert last_id == 0


def test_get_last_sync_state_empty_file(tmp_path):
    f = tmp_path / "state.txt"
    f.write_text("")
    with patch.object(sync, "STATE_FILE", str(f)):
        ts, last_id = sync.get_last_sync_state()
    assert ts == datetime(1970, 1, 1)
    assert last_id == 0


def test_get_last_sync_state_valid(tmp_path):
    f = tmp_path / "state.txt"
    f.write_text("2024-06-01T12:00:00,42")
    with patch.object(sync, "STATE_FILE", str(f)):
        ts, last_id = sync.get_last_sync_state()
    assert ts == datetime(2024, 6, 1, 12, 0, 0)
    assert last_id == 42


def test_save_last_sync_state(tmp_path):
    f = tmp_path / "state.txt"
    with patch.object(sync, "STATE_FILE", str(f)):
        sync.save_last_sync_state(datetime(2024, 6, 1, 12, 0, 0), 7)
    assert f.read_text() == "2024-06-01T12:00:00,7"


def test_save_load_roundtrip(tmp_path):
    f = tmp_path / "state.txt"
    ts = datetime(2025, 3, 15, 9, 30, 0)
    with patch.object(sync, "STATE_FILE", str(f)):
        sync.save_last_sync_state(ts, 99)
        loaded_ts, loaded_id = sync.get_last_sync_state()
    assert loaded_ts == ts
    assert loaded_id == 99


# ---------------------------------------------------------------------------
# sync_users() — DB connections mocked
# ---------------------------------------------------------------------------

def _mock_connections(rows):
    source_cur = MagicMock()
    # Simulate fetchmany: return all rows in one batch, then an empty list sentinel.
    source_cur.fetchmany.side_effect = [list(rows), []]
    source_conn = MagicMock()
    source_conn.cursor.return_value = source_cur

    dest_cur = MagicMock()
    dest_conn = MagicMock()
    dest_conn.cursor.return_value = dest_cur

    return source_conn, source_cur, dest_conn, dest_cur


def test_compound_cursor_advances_to_latest_row(tmp_path):
    t1 = datetime(2024, 1, 1, 10, 0, 0)
    t2 = datetime(2024, 1, 1, 11, 0, 0)
    rows = [
        (1, "Alice", "alice@test.com", t1, None),
        (2, "Bob",   "bob@test.com",   t2, None),
    ]
    src, _, dst, _ = _mock_connections(rows)
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    assert open(sf).read() == f"{t2.isoformat()},2"


def test_compound_cursor_handles_timestamp_tie(tmp_path):
    # Rows sharing the same updated_at — highest id should win.
    t = datetime(2024, 1, 1, 10, 0, 0)
    rows = [
        (3, "Alice", "alice@test.com", t, None),
        (5, "Bob",   "bob@test.com",   t, None),
        (7, "Carol", "carol@test.com", t, None),
    ]
    src, _, dst, _ = _mock_connections(rows)
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    assert open(sf).read() == f"{t.isoformat()},7"


def test_no_rows_does_not_update_state(tmp_path):
    src, _, dst, _ = _mock_connections([])
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    assert not os.path.exists(sf)


def test_upsert_called_for_each_row(tmp_path):
    t = datetime(2024, 1, 1, 10, 0, 0)
    rows = [
        (1, "Alice", "alice@test.com", t, None),
        (2, "Bob",   "bob@test.com",   t, None),
    ]
    src, _, dst, dest_cur = _mock_connections(rows)
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    assert dest_cur.execute.call_count == 2
    dst.commit.assert_called_once()


def test_upsert_sql_contains_on_conflict_do_update(tmp_path):
    # Verifies stale destination rows are overwritten, not silently skipped.
    t = datetime(2024, 1, 1, 10, 0, 0)
    rows = [(1, "Alice", "alice@test.com", t, None)]
    src, _, dst, dest_cur = _mock_connections(rows)
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    sql = dest_cur.execute.call_args[0][0]
    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql


# ---------------------------------------------------------------------------
# Soft-delete handling
# ---------------------------------------------------------------------------

def test_soft_deleted_row_issues_delete_on_destination(tmp_path):
    t = datetime(2024, 1, 1, 10, 0, 0)
    deleted_at = datetime(2024, 6, 1, 12, 0, 0)
    rows = [(1, "Alice", "alice@test.com", t, deleted_at)]
    src, _, dst, dest_cur = _mock_connections(rows)
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    sql, params = dest_cur.execute.call_args[0]
    assert "DELETE" in sql.upper()
    assert params == (1,)


def test_live_and_deleted_rows_handled_in_same_batch(tmp_path):
    # One live row upserted, one deleted row removed — both in a single sync run.
    t = datetime(2024, 1, 1, 10, 0, 0)
    deleted_at = datetime(2024, 6, 1, 12, 0, 0)
    rows = [
        (1, "Alice", "alice@test.com", t, None),
        (2, "Bob",   "bob@test.com",   t, deleted_at),
    ]
    src, _, dst, dest_cur = _mock_connections(rows)
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    assert dest_cur.execute.call_count == 2
    calls = [c[0][0] for c in dest_cur.execute.call_args_list]
    assert any("INSERT" in sql for sql in calls)
    assert any("DELETE" in sql for sql in calls)


# ---------------------------------------------------------------------------
# Rollback on partial failure
# ---------------------------------------------------------------------------

def test_dest_write_failure_triggers_rollback(tmp_path):
    t = datetime(2024, 1, 1, 10, 0, 0)
    rows = [(1, "Alice", "alice@test.com", t, None)]
    src, _, dst, dest_cur = _mock_connections(rows)
    dest_cur.execute.side_effect = Exception("DB write error")
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        with pytest.raises(Exception, match="DB write error"):
            sync.sync_users()

    dst.rollback.assert_called_once()
    dst.commit.assert_not_called()
    assert not os.path.exists(sf)


# ---------------------------------------------------------------------------
# Batching
# ---------------------------------------------------------------------------

def test_multiple_batches_each_committed_separately(tmp_path):
    # Simulates a large result set split across two fetchmany calls.
    # Each batch must be committed independently and advance the cursor.
    t = datetime(2024, 1, 1, 10, 0, 0)
    batch1 = [
        (1, "Alice", "alice@test.com", t, None),
        (2, "Bob",   "bob@test.com",   t, None),
    ]
    batch2 = [
        (3, "Carol", "carol@test.com", t, None),
    ]
    src, source_cur, dst, dest_cur = _mock_connections([])
    source_cur.fetchmany.side_effect = [batch1, batch2, []]
    sf = str(tmp_path / "state.txt")

    with patch("sync.get_source_connection", return_value=src), \
         patch("sync.get_dest_connection",   return_value=dst), \
         patch.object(sync, "STATE_FILE", sf):
        sync.sync_users()

    assert dest_cur.execute.call_count == 3  # one per row across both batches
    assert dst.commit.call_count == 2        # one commit per batch
    assert open(sf).read() == f"{t.isoformat()},3"
