import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("jobs.db")
log = logging.getLogger(__name__)

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    location    TEXT,
    url         TEXT UNIQUE NOT NULL,
    board       TEXT NOT NULL,
    description TEXT,
    fit_score   INTEGER,
    fit_reasoning TEXT,
    status      TEXT NOT NULL DEFAULT 'new',
    applied_at  TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_fit_score ON jobs(fit_score);
CREATE INDEX IF NOT EXISTS idx_jobs_board     ON jobs(board);

CREATE TRIGGER IF NOT EXISTS jobs_updated_at
AFTER UPDATE ON jobs
BEGIN
    UPDATE jobs SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE id = NEW.id;
END;
"""

VALID_STATUSES = {"new", "reviewed", "applied", "interview", "rejected", "offer"}


def init():
    with connect() as conn:
        conn.executescript(SCHEMA)
    log.info("Database ready at %s", DB_PATH)


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_job(title: str, company: str, location: str, url: str, board: str, description: str) -> int | None:
    """Insert job if URL not seen before. Returns new id or None if duplicate."""
    with connect() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE url = ?", (url,)).fetchone()
        if existing:
            return None
        cur = conn.execute(
            "INSERT INTO jobs (title, company, location, url, board, description) VALUES (?,?,?,?,?,?)",
            (title, company, location, url, board, description),
        )
        return cur.lastrowid


def update_score(job_id: int, score: int, reasoning: str):
    with connect() as conn:
        conn.execute(
            "UPDATE jobs SET fit_score=?, fit_reasoning=? WHERE id=?",
            (score, reasoning, job_id),
        )


def update_status(job_id: int, status: str, applied_at: str | None = None):
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    with connect() as conn:
        if applied_at:
            conn.execute(
                "UPDATE jobs SET status=?, applied_at=? WHERE id=?",
                (status, applied_at, job_id),
            )
        else:
            conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))


def get_job(job_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def list_jobs(
    status: str | None = None,
    min_score: int | None = None,
    board: str | None = None,
    order_by: str = "fit_score DESC",
    limit: int = 200,
) -> list[sqlite3.Row]:
    clauses, params = [], []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if min_score is not None:
        clauses.append("fit_score >= ?")
        params.append(min_score)
    if board:
        clauses.append("board = ?")
        params.append(board)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    safe_order = order_by if order_by in (
        "fit_score DESC", "fit_score ASC", "created_at DESC", "company ASC"
    ) else "fit_score DESC"
    sql = f"SELECT * FROM jobs {where} ORDER BY {safe_order} LIMIT ?"
    params.append(limit)
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def get_unscored_jobs() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM jobs WHERE fit_score IS NULL").fetchall()


def stats() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by_status = {
            r["status"]: r["cnt"]
            for r in conn.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status").fetchall()
        }
        avg_score = conn.execute("SELECT AVG(fit_score) FROM jobs WHERE fit_score IS NOT NULL").fetchone()[0]
    return {"total": total, "by_status": by_status, "avg_score": round(avg_score or 0, 1)}
