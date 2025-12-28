from __future__ import annotations
import os
import sqlite3
import uuid
from typing import Optional, List

from .interfaces import Repository
from .models import Interpretation, Quota, VoiceSettings, User

class SqliteRepository(Repository):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Ensure database file exists
        sqlite3.connect(self.db_path).close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Pragmas for better durability/consistency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def apply_migrations(self) -> None:
        here = os.path.dirname(__file__)
        mig_dir = os.path.join(here, "migrations", "sqlite")
        versions = sorted([f for f in os.listdir(mig_dir) if f.endswith(".sql")])
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            seen = {row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
            for v in versions:
                if v in seen:
                    continue
                path = os.path.join(mig_dir, v)
                with open(path, "r", encoding="utf-8") as f:
                    sql = f.read()
                conn.executescript(sql)
                conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (v,))

    # Users
    def create_user(self, email: str, password_hash: str) -> User:
        user_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users(id, email, password_hash, is_verified) VALUES (?, ?, ?, 1)",
                (user_id, email, password_hash)
            )
        return User(id=user_id, email=email, password_hash=password_hash, is_verified=True, created_at=None)

    def get_user_by_email(self, email: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute("SELECT id, email, password_hash, is_verified, created_at FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            is_verified=bool(row["is_verified"]),
            created_at=row["created_at"]
        )

    # Interpretations
    def save_interpretation(self, id_: str, explanation: str, confidence: float, user_id: Optional[str] = None, image_path: Optional[str] = None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO interpretations(id, user_id, explanation, confidence, image_path) VALUES (?, ?, ?, ?, ?)",
                (id_, user_id, explanation, float(confidence), image_path),
            )

    def get_interpretation(self, id_: str) -> Optional[Interpretation]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, user_id, explanation, confidence, image_path, created_at FROM interpretations WHERE id = ?",
                (id_,),
            ).fetchone()
        if not row:
            return None
        return Interpretation(
            id=row["id"],
            user_id=row["user_id"],
            explanation=row["explanation"],
            confidence=float(row["confidence"]),
            image_path=row["image_path"],
            created_at=row["created_at"],
        )

    def list_interpretations(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Interpretation]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, user_id, explanation, confidence, image_path, created_at FROM interpretations WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, int(limit), int(offset)),
            ).fetchall()
        return [
            Interpretation(
                id=r["id"],
                user_id=r["user_id"],
                explanation=r["explanation"],
                confidence=float(r["confidence"]),
                image_path=r["image_path"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # Quotas (minimal placeholder)
    def get_quota(self, user_id: str) -> Optional[Quota]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, period_start, count FROM quotas WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return Quota(user_id=row["user_id"], period_start=row["period_start"], count=int(row["count"]))

    def increment_quota(self, user_id: str, period: str = "monthly") -> Quota:
        # Simplified: upsert with naive monthly period_start = first day of current month (SQLite strftime trick)
        with self._connect() as conn:
            period_start = conn.execute("SELECT strftime('%Y-%m-01T00:00:00Z','now')").fetchone()[0]
            row = conn.execute("SELECT count FROM quotas WHERE user_id = ?", (user_id,)).fetchone()
            if row is None:
                conn.execute("INSERT INTO quotas(user_id, period_start, count) VALUES (?, ?, ?)", (user_id, period_start, 1))
                c = 1
            else:
                c = int(row[0]) + 1
                conn.execute("UPDATE quotas SET count = ?, period_start = ? WHERE user_id = ?", (c, period_start, user_id))
        return Quota(user_id=user_id, period_start=period_start, count=c)

    # Voice settings (minimal)
    def get_voice_settings(self, user_id: str) -> Optional[VoiceSettings]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, voice_id, rate, pitch, volume FROM voice_settings WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if not row:
            return None
        return VoiceSettings(
            user_id=row["user_id"],
            voice_id=row["voice_id"],
            rate=row["rate"],
            pitch=row["pitch"],
            volume=row["volume"],
        )

    def upsert_voice_settings(self, user_id: str, s: VoiceSettings) -> None:
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM voice_settings WHERE user_id = ?", (user_id,)).fetchone()
            if exists:
                conn.execute(
                    "UPDATE voice_settings SET voice_id = ?, rate = ?, pitch = ?, volume = ? WHERE user_id = ?",
                    (s.voice_id, s.rate, s.pitch, s.volume, user_id),
                )
            else:
                conn.execute(
                    "INSERT INTO voice_settings(user_id, voice_id, rate, pitch, volume) VALUES (?, ?, ?, ?, ?)",
                    (user_id, s.voice_id, s.rate, s.pitch, s.volume),
                )
