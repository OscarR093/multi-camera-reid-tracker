import sqlite3
import pickle
import time
import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class SQLiteClient:
    def __init__(self, db_path: str = "data/persons.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _create_tables(self):
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    global_id TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    embedding BLOB,
                    height REAL,
                    timestamp REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_global_id
                ON events(global_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_camera
                ON events(camera_id)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    created_at REAL NOT NULL
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blacklist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    global_id TEXT,
                    description TEXT,
                    reason TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at REAL NOT NULL,
                    active INTEGER DEFAULT 1
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS hourly_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id TEXT NOT NULL,
                    hour TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    UNIQUE(camera_id, hour)
                )
                """
            )

    def log_event(
        self,
        global_id: str,
        camera_id: str,
        event_type: str,
        embedding: Optional[np.ndarray] = None,
        height: Optional[float] = None,
        timestamp: Optional[float] = None,
    ):
        if timestamp is None:
            timestamp = time.time()

        emb_bytes = None
        if embedding is not None:
            emb_bytes = pickle.dumps(embedding)

        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO events (global_id, camera_id, event_type, embedding, height, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (global_id, camera_id, event_type, emb_bytes, height, timestamp),
            )

    def get_events(
        self,
        camera_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        with self._get_conn() as conn:
            if camera_id:
                rows = conn.execute(
                    "SELECT * FROM events WHERE camera_id = ? "
                    "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (camera_id, limit, offset),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events "
                    "ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()

            return [dict(row) for row in rows]

    def save_hourly_count(
        self, camera_id: str, hour: str, count: int
    ):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO hourly_counts (camera_id, hour, count) "
                "VALUES (?, ?, ?)",
                (camera_id, hour, count),
            )

    def get_hourly_counts(
        self, hours: int = 24
    ) -> List[Dict]:
        with self._get_conn() as conn:
            from datetime import datetime, timedelta
            since = (datetime.now() - timedelta(hours=hours)).strftime(
                "%Y-%m-%d %H:00"
            )
            rows = conn.execute(
                "SELECT * FROM hourly_counts WHERE hour >= ? ORDER BY hour ASC",
                (since,),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_user(
        self, username: str, password_hash: str, role: str = "viewer"
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash, role, created_at) "
                "VALUES (?, ?, ?, ?)",
                (username, password_hash, role, time.time()),
            )
            return cursor.lastrowid

    def get_user(self, username: str) -> Optional[Dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None

    def get_users(self) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, username, role, created_at FROM users"
            ).fetchall()
            return [dict(row) for row in rows]

    def add_blacklist_entry(
        self,
        global_id: Optional[str] = None,
        description: Optional[str] = None,
        reason: Optional[str] = None,
        created_by: Optional[int] = None,
    ) -> int:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO blacklist (global_id, description, reason, created_by, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (global_id, description, reason, created_by, time.time()),
            )
            return cursor.lastrowid

    def get_blacklist(self, active_only: bool = True) -> List[Dict]:
        with self._get_conn() as conn:
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM blacklist WHERE active = 1"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM blacklist"
                ).fetchall()
            return [dict(row) for row in rows]

    def deactivate_blacklist_entry(self, entry_id: int):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE blacklist SET active = 0 WHERE id = ?",
                (entry_id,),
            )
