import os
import sqlite3
from typing import Optional, Tuple, Dict

DB_DIR = os.path.join(os.getcwd(), "data")
DB_PATH = os.path.join(DB_DIR, "history.db")


def init_db(path: Optional[str] = None) -> None:
    db_path = path or DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interpretations (
                id TEXT PRIMARY KEY,
                explanation TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_interpretation(id_: str, explanation: str, confidence: float, path: Optional[str] = None) -> None:
    db_path = path or DB_PATH
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO interpretations (id, explanation, confidence) VALUES (?, ?, ?)",
            (id_, explanation, float(confidence)),
        )


def get_interpretation(id_: str, path: Optional[str] = None) -> Optional[Tuple[str, str, float, str]]:
    db_path = path or DB_PATH
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute(
            "SELECT id, explanation, confidence, created_at FROM interpretations WHERE id = ?",
            (id_,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return (row[0], row[1], float(row[2]), str(row[3]))
