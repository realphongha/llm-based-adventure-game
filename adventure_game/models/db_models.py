from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS game_state (
    slot TEXT PRIMARY KEY,
    state_json TEXT NOT NULL,
    summary TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
"""


class GameStateRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def load(self, slot: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT state_json, summary FROM game_state WHERE slot = ?", (slot,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            state = json.loads(row[0])
            state["summary"] = row[1]
            return state

    def save(
        self,
        slot: str,
        *,
        game_state: Dict[str, Any],
        summary: Optional[str],
    ) -> None:
        payload = json.dumps(game_state)
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO game_state (slot, state_json, summary, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(slot) DO UPDATE SET
                    state_json = excluded.state_json,
                    summary = excluded.summary,
                    updated_at = excluded.updated_at
                """,
                (slot, payload, summary, now, now),
            )
            conn.commit()
