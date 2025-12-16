"""
SQLite 기반 API 엔드포인트/설정 저장소.

목적:
- 응급 상황 전송을 위한 API 엔드포인트 목록 관리
- Gradio 재시작에도 설정이 유지되도록 함
- Primary API의 base_url / watch_id 등도 저장 가능

보안:
- 시크릿(토큰 등)을 저장하지 않음. (URL/watch_id는 운영 설정값으로 간주)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ApiEndpointDB:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        """데이터베이스 초기화 (테이블 생성)"""
        with self.connect() as conn:
            # API 엔드포인트 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_endpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    method TEXT NOT NULL DEFAULT 'POST',
                    type TEXT NOT NULL DEFAULT 'multipart',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            # 앱 설정 키-값 테이블
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_kv (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    # ----------------------------
    # Config (key/value)
    # ----------------------------
    def get_kv(self, key: str) -> Optional[str]:
        """키-값 설정 가져오기"""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM app_kv WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else None

    def set_kv(self, key: str, value: str) -> None:
        """키-값 설정 저장"""
        now = _now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO app_kv(key, value, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()

    # ----------------------------
    # Endpoints CRUD
    # ----------------------------
    def list_endpoints(self) -> List[Dict[str, Any]]:
        """모든 엔드포인트 목록 가져오기"""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, url, method, type, enabled, created_at, updated_at
                FROM api_endpoints
                ORDER BY id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def insert_endpoint(
        self,
        name: str,
        url: str,
        method: str = "POST",
        endpoint_type: str = "multipart",
        enabled: bool = True,
    ) -> int:
        """새 엔드포인트 추가"""
        now = _now_iso()
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO api_endpoints(name, url, method, type, enabled, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    url,
                    method.upper(),
                    endpoint_type,
                    1 if enabled else 0,
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_endpoint(
        self,
        endpoint_id: int,
        *,
        name: Optional[str] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
        endpoint_type: Optional[str] = None,
        enabled: Optional[bool] = None,
    ) -> None:
        """엔드포인트 수정"""
        fields: List[Tuple[str, Any]] = []
        if name is not None:
            fields.append(("name", name))
        if url is not None:
            fields.append(("url", url))
        if method is not None:
            fields.append(("method", method.upper()))
        if endpoint_type is not None:
            fields.append(("type", endpoint_type))
        if enabled is not None:
            fields.append(("enabled", 1 if enabled else 0))

        if not fields:
            return

        sets = ", ".join([f"{k} = ?" for k, _ in fields] + ["updated_at = ?"])
        params = [v for _, v in fields] + [_now_iso(), endpoint_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE api_endpoints SET {sets} WHERE id = ?", params)
            conn.commit()

    def delete_endpoint(self, endpoint_id: int) -> None:
        """엔드포인트 삭제"""
        with self.connect() as conn:
            conn.execute("DELETE FROM api_endpoints WHERE id = ?", (endpoint_id,))
            conn.commit()

    def get_enabled_endpoints(self) -> List[Dict[str, Any]]:
        """활성화된 엔드포인트만 가져오기"""
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, url, method, type, enabled, created_at, updated_at
                FROM api_endpoints
                WHERE enabled = 1
                ORDER BY id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]
