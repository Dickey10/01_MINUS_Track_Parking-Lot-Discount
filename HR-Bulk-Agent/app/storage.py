import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import settings
from app.security import digest, hash_password, mask_payload


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = settings.db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                employee_hash TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                target_platforms_json TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                approved_by TEXT,
                status TEXT NOT NULL,
                memo TEXT,
                validation_errors_json TEXT NOT NULL,
                previews_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS platform_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                change_request_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                request_ref TEXT,
                masked_payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                employee_hash TEXT,
                target TEXT,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                can_create INTEGER NOT NULL DEFAULT 0,
                can_update INTEGER NOT NULL DEFAULT 0,
                can_delete INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                is_secret INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS employee_master (
                employee_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        admin_count = conn.execute("SELECT COUNT(*) AS cnt FROM accounts WHERE role = 'admin'").fetchone()["cnt"]
        if admin_count == 0:
            now = utc_now()
            conn.execute(
                """
                INSERT INTO accounts
                (username, display_name, password_hash, role, can_create, can_update, can_delete, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, 1, 1, ?, ?)
                """,
                ("admin", "관리자", hash_password("admin123!"), "admin", now, now),
            )


def audit(actor: str, action: str, employee_id: str | None, target: str, details: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (actor, action, employee_hash, target, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                actor,
                action,
                digest(employee_id) if employee_id else None,
                target,
                json.dumps(mask_payload(details), ensure_ascii=False),
                utc_now(),
            ),
        )
