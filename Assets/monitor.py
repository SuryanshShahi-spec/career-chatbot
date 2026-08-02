"""
monitor.py — Lightweight SQLite-backed monitoring for Job Search Assistant.

Tracks:
  - search_events  : per-Adzuna-call performance (latency, results, errors)
  - api_calls      : per-call health for every external service
  - chat_sessions  : per-run() user engagement summary

Usage:
    from monitor import monitor          # singleton instance
    monitor.record_search(...)
    monitor.record_api_call(...)
    monitor.record_session(...)
    stats = monitor.get_summary()
"""

import os
import sqlite3
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────────

_BASE_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
METRICS_DIR = os.path.join(_BASE_DIR, "metrics")
DB_PATH     = os.path.join(METRICS_DIR, "metrics.db")

os.makedirs(METRICS_DIR, exist_ok=True)

# ── Internal logger (never raises — monitoring must not break the app) ──────────

_log = logging.getLogger("monitor")
if not _log.handlers:
    _log.setLevel(logging.WARNING)
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s [monitor]: %(message)s"))
    _log.addHandler(_h)

# ── DDL ────────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS search_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                TEXT    NOT NULL,          -- ISO-8601 UTC
    job_title         TEXT    NOT NULL,
    location          TEXT    NOT NULL,
    country_code      TEXT    NOT NULL DEFAULT 'in',
    results_requested INTEGER NOT NULL DEFAULT 5,
    results_returned  INTEGER NOT NULL DEFAULT 0,
    total_available   INTEGER NOT NULL DEFAULT 0,
    latency_ms        REAL    NOT NULL DEFAULT 0,
    status            TEXT    NOT NULL,          -- 'success' | 'no_results' | 'error'
    error_type        TEXT                       -- NULL on success
);

CREATE TABLE IF NOT EXISTS api_calls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    service     TEXT    NOT NULL,                -- 'adzuna' | 'groq' | 'tavily'
    endpoint    TEXT    NOT NULL,                -- e.g. 'job_search', 'chat_completion'
    latency_ms  REAL    NOT NULL DEFAULT 0,
    status_code INTEGER NOT NULL DEFAULT 0,      -- 0 = non-HTTP error
    success     INTEGER NOT NULL DEFAULT 0,      -- 1 = True, 0 = False
    error_type  TEXT,                            -- NULL on success
    retries     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       TEXT    NOT NULL UNIQUE,
    started_at       TEXT    NOT NULL,
    ended_at         TEXT,
    duration_s       REAL,
    message_count    INTEGER NOT NULL DEFAULT 0,
    tool_calls       INTEGER NOT NULL DEFAULT 0,
    unique_titles    INTEGER NOT NULL DEFAULT 0,
    unique_locations INTEGER NOT NULL DEFAULT 0,
    error_count      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_search_ts      ON search_events(ts);
CREATE INDEX IF NOT EXISTS ix_search_status  ON search_events(status);
CREATE INDEX IF NOT EXISTS ix_api_service    ON api_calls(service);
CREATE INDEX IF NOT EXISTS ix_session_id     ON chat_sessions(session_id);
"""


# ── MonitorDB class ────────────────────────────────────────────────────────────

class MonitorDB:
    """
    Thread-safe SQLite metrics store.

    All public methods silently swallow exceptions so monitoring never
    crashes the main application.
    """

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        try:
            with self._lock:
                conn = self._connect()
                try:
                    conn.executescript(_DDL)
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            _log.warning("Could not initialise metrics DB: %s", exc)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ── Public record methods ──────────────────────────────────────────────────

    def record_search(
        self,
        job_title: str,
        location: str,
        country_code: str,
        results_requested: int,
        results_returned: int,
        total_available: int,
        latency_ms: float,
        status: str,                     # 'success' | 'no_results' | 'error'
        error_type: Optional[str] = None,
    ) -> None:
        """Record one Adzuna search event."""
        try:
            with self._lock:
                conn = self._connect()
                try:
                    conn.execute(
                        """
                        INSERT INTO search_events
                            (ts, job_title, location, country_code,
                             results_requested, results_returned, total_available,
                             latency_ms, status, error_type)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            self._now(), job_title, location, country_code,
                            results_requested, results_returned, total_available,
                            round(latency_ms, 2), status, error_type,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            _log.warning("record_search failed: %s", exc)

    def record_api_call(
        self,
        service: str,
        endpoint: str,
        latency_ms: float,
        status_code: int = 200,
        success: bool = True,
        error_type: Optional[str] = None,
        retries: int = 0,
    ) -> None:
        """Record one external API call (any service)."""
        try:
            with self._lock:
                conn = self._connect()
                try:
                    conn.execute(
                        """
                        INSERT INTO api_calls
                            (ts, service, endpoint, latency_ms,
                             status_code, success, error_type, retries)
                        VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (
                            self._now(), service, endpoint, round(latency_ms, 2),
                            status_code, int(success), error_type, retries,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            _log.warning("record_api_call failed: %s", exc)

    def record_session(
        self,
        session_id: str,
        started_at: str,
        ended_at: str,
        duration_s: float,
        message_count: int,
        tool_calls: int,
        unique_titles: int,
        unique_locations: int,
        error_count: int,
    ) -> None:
        """Record a completed chat session's engagement metrics."""
        try:
            with self._lock:
                conn = self._connect()
                try:
                    conn.execute(
                        """
                        INSERT INTO chat_sessions
                            (session_id, started_at, ended_at, duration_s,
                             message_count, tool_calls, unique_titles,
                             unique_locations, error_count)
                        VALUES (?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(session_id) DO UPDATE SET
                            ended_at         = excluded.ended_at,
                            duration_s       = excluded.duration_s,
                            message_count    = excluded.message_count,
                            tool_calls       = excluded.tool_calls,
                            unique_titles    = excluded.unique_titles,
                            unique_locations = excluded.unique_locations,
                            error_count      = excluded.error_count
                        """,
                        (
                            session_id, started_at, ended_at, round(duration_s, 2),
                            message_count, tool_calls, unique_titles,
                            unique_locations, error_count,
                        ),
                    )
                    conn.commit()
                finally:
                    conn.close()
        except Exception as exc:
            _log.warning("record_session failed: %s", exc)

    # ── Query helpers used by dashboard ───────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Return a dict of aggregate statistics for the dashboard.
        Keys: search_stats, top_titles, top_locations, zero_result_queries,
              api_health, session_stats, recent_errors.
        """
        try:
            with self._lock:
                conn = self._connect()
                try:
                    return {
                        "search_stats":       self._search_stats(conn),
                        "top_titles":         self._top_values(conn, "job_title", 5),
                        "top_locations":      self._top_values(conn, "location", 5),
                        "zero_result_queries":self._zero_result_queries(conn, 10),
                        "api_health":         self._api_health(conn),
                        "session_stats":      self._session_stats(conn),
                        "recent_errors":      self._recent_errors(conn, 10),
                    }
                finally:
                    conn.close()
        except Exception as exc:
            _log.warning("get_summary failed: %s", exc)
            return {}

    # ── Private query methods ──────────────────────────────────────────────────

    @staticmethod
    def _search_stats(conn: sqlite3.Connection) -> dict:
        row = conn.execute("""
            SELECT
                COUNT(*)                                          AS total_searches,
                SUM(CASE WHEN status='success'    THEN 1 ELSE 0 END) AS successful,
                SUM(CASE WHEN status='no_results' THEN 1 ELSE 0 END) AS no_results,
                SUM(CASE WHEN status='error'      THEN 1 ELSE 0 END) AS errors,
                ROUND(AVG(latency_ms), 1)                        AS avg_latency_ms,
                ROUND(MIN(latency_ms), 1)                        AS min_latency_ms,
                ROUND(MAX(latency_ms), 1)                        AS max_latency_ms,
                SUM(results_returned)                            AS total_results_delivered,
                COUNT(DISTINCT job_title)                        AS unique_titles_searched,
                COUNT(DISTINCT location)                         AS unique_locations_searched
            FROM search_events
        """).fetchone()
        return dict(row) if row else {}

    @staticmethod
    def _top_values(conn: sqlite3.Connection, column: str, limit: int) -> list:
        rows = conn.execute(f"""
            SELECT {column} AS value, COUNT(*) AS count
            FROM search_events
            GROUP BY {column}
            ORDER BY count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _zero_result_queries(conn: sqlite3.Connection, limit: int) -> list:
        rows = conn.execute("""
            SELECT job_title, location, COUNT(*) AS attempts, MAX(ts) AS last_attempt
            FROM search_events
            WHERE status = 'no_results'
            GROUP BY job_title, location
            ORDER BY attempts DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _api_health(conn: sqlite3.Connection) -> list:
        rows = conn.execute("""
            SELECT
                service,
                endpoint,
                COUNT(*)                                          AS total_calls,
                SUM(CASE WHEN success=1 THEN 1 ELSE 0 END)       AS successful,
                ROUND(AVG(latency_ms), 1)                        AS avg_latency_ms,
                ROUND(MAX(latency_ms), 1)                        AS max_latency_ms,
                ROUND(
                    100.0 * SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) / COUNT(*),
                    1
                )                                                AS success_rate_pct,
                SUM(retries)                                     AS total_retries
            FROM api_calls
            GROUP BY service, endpoint
            ORDER BY service, endpoint
        """).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _session_stats(conn: sqlite3.Connection) -> dict:
        row = conn.execute("""
            SELECT
                COUNT(*)                                 AS total_sessions,
                ROUND(AVG(duration_s),   1)              AS avg_duration_s,
                ROUND(AVG(message_count),1)              AS avg_messages,
                ROUND(AVG(tool_calls),   1)              AS avg_tool_calls,
                SUM(message_count)                       AS total_messages,
                SUM(tool_calls)                          AS total_tool_calls,
                SUM(error_count)                         AS total_errors
            FROM chat_sessions
        """).fetchone()
        return dict(row) if row else {}

    @staticmethod
    def _recent_errors(conn: sqlite3.Connection, limit: int) -> list:
        rows = conn.execute("""
            SELECT ts, 'search' AS source, job_title AS context, error_type
            FROM search_events
            WHERE status = 'error'
            UNION ALL
            SELECT ts, service AS source, endpoint AS context, error_type
            FROM api_calls
            WHERE success = 0 AND error_type IS NOT NULL
            ORDER BY ts DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


# ── Singleton ─────────────────────────────────────────────────────────────────

monitor = MonitorDB()
