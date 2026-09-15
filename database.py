import sqlite3
import json
from datetime import datetime

DB_NAME = "chatroom.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            personality TEXT NOT NULL,
            speech_style TEXT NOT NULL,
            backstory TEXT DEFAULT '',
            sample_lines TEXT DEFAULT '[]',
            relationships TEXT DEFAULT '{}',
            triggers TEXT DEFAULT '[]',
            interrupt_tendency TEXT DEFAULT 'medium',
            assertiveness TEXT DEFAULT 'medium'
        )
    """)

    # Migrations: older databases predate these columns.
    cursor.execute("PRAGMA table_info(characters)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if "backstory" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN backstory TEXT DEFAULT ''")
    if "sample_lines" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN sample_lines TEXT DEFAULT '[]'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def add_character(name, personality, speech_style, backstory="", sample_lines=None,
                   relationships=None, triggers=None, interrupt_tendency="medium",
                   assertiveness="medium"):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO characters
               (name, personality, speech_style, backstory, sample_lines, relationships, triggers, interrupt_tendency, assertiveness)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, personality, speech_style, backstory, json.dumps(sample_lines or []),
             json.dumps(relationships or {}), json.dumps(triggers or []),
             interrupt_tendency, assertiveness)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_character(name, personality, speech_style, backstory="", sample_lines=None,
                      relationships=None, triggers=None, interrupt_tendency="medium",
                      assertiveness="medium"):
    """Overwrites every field for an already-seeded character, so re-running
    seed_characters.py keeps existing rows in sync with edits to CHARACTERS."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE characters
               SET personality = ?, speech_style = ?, backstory = ?, sample_lines = ?,
                   relationships = ?, triggers = ?, interrupt_tendency = ?, assertiveness = ?
               WHERE name = ?""",
            (personality, speech_style, backstory, json.dumps(sample_lines or []),
             json.dumps(relationships or {}), json.dumps(triggers or []),
             interrupt_tendency, assertiveness, name)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_characters():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM characters")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_session(name):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (name, created_at) VALUES (?, ?)",
            (name, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def add_message(session_id, sender, content):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, sender, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, sender, content, datetime.now().isoformat())
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_messages(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()