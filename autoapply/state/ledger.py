"""state/ledger.py — never apply twice. job_url UNIQUE is the whole mechanism."""
from __future__ import annotations
import sqlite3, time
from pathlib import Path

import paths

DB = paths.under("ledger.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
  app_id     TEXT PRIMARY KEY,
  job_url    TEXT UNIQUE NOT NULL,
  platform   TEXT NOT NULL,
  status     TEXT NOT NULL,   -- discovered|started|checkpointed|submitted|failed|abandoned
  rung       INTEGER,
  attempts   INTEGER DEFAULT 0,
  cost_inr   REAL DEFAULT 0,
  human_secs INTEGER DEFAULT 0,
  created_at TEXT, updated_at TEXT
);
"""

def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.execute(SCHEMA)
    return con

def register(con, app_id: str, job_url: str, platform: str) -> bool:
    """Returns False if job_url already seen — caller must skip."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        con.execute(
            "INSERT INTO applications (app_id, job_url, platform, status, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?)", (app_id, job_url, platform, "discovered", now, now))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def lookup(con, job_url: str) -> dict | None:
    """Existing row for this URL, or None. Distinguishes 'already submitted,
    skip' from 'crashed halfway, resume' — register() alone cannot."""
    con.row_factory = sqlite3.Row
    cur = con.execute("SELECT * FROM applications WHERE job_url=?", (job_url,))
    row = cur.fetchone()
    return dict(row) if row else None

def set_status(con, app_id: str, status: str, **fields) -> None:
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    sets = ", ".join([f"{k}=?" for k in fields] + ["status=?", "updated_at=?"])
    con.execute(f"UPDATE applications SET {sets} WHERE app_id=?",
                (*fields.values(), status, now, app_id))
    con.commit()
