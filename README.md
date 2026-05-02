# 🛠️ Database Sync Debug Lab

> A hands-on lab that simulates a real-world incremental PostgreSQL sync pipeline — practise diagnosing and fixing common data integration bugs including timestamp collisions, stale records, schema drift, and partial failures.

![Language](https://img.shields.io/badge/language-Python-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/status-active-brightgreen?style=flat-square)

---

## 🎯 Overview

A debug lab built around a realistic incremental sync pipeline. The sync script reads new and updated rows from a source PostgreSQL database and writes them to a destination PostgreSQL database using a compound cursor (`updated_at + id`) to avoid missed or duplicate records.

The lab includes intentional bug scenarios, runbooks for investigating each one, and a full unit test suite — designed to reflect the kind of data integration work done in technical support and data engineering roles.

---

## 🧰 Tech Stack

- **Language** — Python 3.8+
- **Databases** — PostgreSQL 15 (source + destination)
- **Libraries** — psycopg2-binary, python-dotenv, pytest
- **Infrastructure** — Docker Compose
- **Output** — Structured logs via Python `logging`

---

## 📁 Project Structure

```
database-sync-debug-lab/
├── src/
│   ├── sync.py           # Main sync script — compound cursor, batching, soft deletes
│   ├── db.py             # Connection helpers for source and destination
│   ├── config.py         # Centralised config, all values env-overridable
│   └── logger.py         # Shared logger for the pipeline
├── tests/
│   └── test_sync.py      # Unit tests — cursor, upsert, soft delete, rollback, batching
├── sql/
│   ├── source_schema.sql      # users table for sourcedb
│   ├── destination_schema.sql # users table for destdb
│   ├── seed_data.sql          # Baseline rows (Alice, Bob)
│   └── broken_scenarios.sql   # SQL to reproduce known bugs manually
├── scenarios/
│   ├── timestamp_collision_bug.md
│   ├── duplicate_records_on_retry.md
│   ├── schema_drift.md
│   ├── failed_incremental_sync.md
│   ├── permissions_error.md
│   └── slow_query.md
├── runbooks/
│   ├── timestamp_collision_runbook.md
│   ├── duplicate_records_on_retry_runbook.md
│   ├── schema_drift_runbook.md
│   ├── sync_failure_troubleshooting.md
│   ├── query_plan_analysis.md
│   └── customer_escalation_template.md
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── last_sync.txt         # Persists the compound cursor between runs
```

---

## 🚀 Getting Started

### ✅ Prerequisites

- Docker installed and running
- Python 3.8+
- pip installed

### ▶️ Step 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### ▶️ Step 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` if you need to override any defaults (host, port, credentials, batch size). The defaults work out of the box with the Docker Compose setup.

### ▶️ Step 3 — Start the databases

```bash
docker compose up -d
```

Starts two PostgreSQL 15 containers:

| Container | Database | Port |
|---|---|---|
| `source_db` | `sourcedb` | `5433` |
| `destination_db` | `destdb` | `5434` |

Both use credentials `demo / demo`. The source is seeded with two users (Alice and Bob).

### ▶️ Step 4 — Run the sync

```bash
python src/sync.py
```

On first run all rows are synced. Subsequent runs only process rows changed since the last cursor position saved in `last_sync.txt`.

---

## 🔍 How the Sync Works

| Feature | Detail |
|---|---|
| **Incremental cursor** | Compound `updated_at + id` — avoids skipping rows that share the same timestamp |
| **Upsert** | `ON CONFLICT (id) DO UPDATE` — destination rows stay in sync even on retry |
| **Soft deletes** | Rows with `deleted_at` set are removed from the destination |
| **Batching** | `fetchmany(BATCH_SIZE)` — bounded memory use; cursor saved per batch |
| **Rollback** | Any write failure triggers `dest_conn.rollback()` before re-raising |

---

## 🧪 Running Tests

```bash
pytest tests/
```

14 unit tests covering cursor state read/write, incremental query correctness, upsert behaviour, soft delete handling, rollback on failure, and multi-batch processing. No database connection required — DB calls are mocked.

---

## 🐛 Scenarios & Runbooks

Each scenario file describes a bug and its matching runbook provides step-by-step diagnosis and resolution.

| Scenario | Runbook |
|---|---|
| Timestamp collision — rows silently skipped | `runbooks/timestamp_collision_runbook.md` |
| Stale destination records after retry | `runbooks/duplicate_records_on_retry_runbook.md` |
| Schema drift — new column breaks sync | `runbooks/schema_drift_runbook.md` |
| Sync failure troubleshooting | `runbooks/sync_failure_troubleshooting.md` |
| Slow query — missing index | `runbooks/query_plan_analysis.md` |
| Customer escalation | `runbooks/customer_escalation_template.md` |

Use `sql/broken_scenarios.sql` to reproduce each bug manually against a live database without running the full sync script.

---

## ⚙️ Configuration

All settings are read from environment variables. Copy `.env.example` to `.env` to override any of them:

| Variable | Default | Description |
|---|---|---|
| `SOURCE_HOST` | `localhost` | Source DB host |
| `SOURCE_PORT` | `5433` | Source DB port |
| `SOURCE_DB` | `sourcedb` | Source database name |
| `DEST_HOST` | `localhost` | Destination DB host |
| `DEST_PORT` | `5434` | Destination DB port |
| `DEST_DB` | `destdb` | Destination database name |
| `DB_USER` | `demo` | Username for both databases |
| `DB_PASSWORD` | `demo` | Password for both databases |
| `STATE_FILE` | `last_sync.txt` | Path to cursor state file |
| `BATCH_SIZE` | `500` | Rows fetched per batch |

---

## 🚧 Status

| Feature | Status |
|---|---|
| Compound cursor incremental sync | ✅ Done |
| Upsert with conflict handling | ✅ Done |
| Soft-delete propagation | ✅ Done |
| Batched fetching | ✅ Done |
| Rollback on partial failure | ✅ Done |
| Centralised config + `.env` support | ✅ Done |
| Unit test suite (14 tests) | ✅ Done |
| Bug scenarios + runbooks | ✅ Done |
| Integration tests (live DB) | 🔜 Planned |

---

## 👤 Author

**Mustapha Abella**
Senior Technical Support Engineer
Focused on API-driven SaaS, data integration, and developer-facing support

[github.com/mabella1](https://github.com/mabella1)
