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
            assertiveness TEXT DEFAULT 'medium',
            world_context TEXT DEFAULT '',
            show TEXT DEFAULT 'Custom',
            avatar TEXT DEFAULT ''
        )
    """)

    # Migrations: older databases predate these columns.
    cursor.execute("PRAGMA table_info(characters)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if "backstory" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN backstory TEXT DEFAULT ''")
    if "sample_lines" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN sample_lines TEXT DEFAULT '[]'")
    if "world_context" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN world_context TEXT DEFAULT ''")
    if "show" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN show TEXT DEFAULT 'Custom'")
    if "avatar" not in existing_columns:
        cursor.execute("ALTER TABLE characters ADD COLUMN avatar TEXT DEFAULT ''")

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

    # Which characters are "in the room" for a given session. A session with
    # no rows here (every session created before this feature, or a new one
    # where nobody picked a subset) falls back to every character - see
    # get_session_characters().
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS session_characters (
            session_id INTEGER NOT NULL,
            character_id INTEGER NOT NULL,
            PRIMARY KEY (session_id, character_id),
            FOREIGN KEY (session_id) REFERENCES sessions (id),
            FOREIGN KEY (character_id) REFERENCES characters (id)
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def add_character(name, personality, speech_style, backstory="", sample_lines=None,
                   relationships=None, triggers=None, interrupt_tendency="medium",
                   assertiveness="medium", world_context="", show="Custom", avatar=""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO characters
               (name, personality, speech_style, backstory, sample_lines, relationships, triggers, interrupt_tendency, assertiveness, world_context, show, avatar)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, personality, speech_style, backstory, json.dumps(sample_lines or []),
             json.dumps(relationships or {}), json.dumps(triggers or []),
             interrupt_tendency, assertiveness, world_context, show or "Custom", avatar or "")
        )
        conn.commit()
    except Exception:
        # Without this, a failed INSERT can leave the next call on this file
        # failing with "database is locked" - a timing-sensitive race, not
        # guaranteed on every failure, but real and worth avoiding here.
        conn.rollback()
        raise
    finally:
        conn.close()


def update_character(name, personality, speech_style, backstory="", sample_lines=None,
                      relationships=None, triggers=None, interrupt_tendency="medium",
                      assertiveness="medium", world_context="", show="Custom", avatar=""):
    """Overwrites every field for an already-seeded character, so re-running
    seed_characters.py keeps existing rows in sync with edits to CHARACTERS."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE characters
               SET personality = ?, speech_style = ?, backstory = ?, sample_lines = ?,
                   relationships = ?, triggers = ?, interrupt_tendency = ?, assertiveness = ?,
                   world_context = ?, show = ?, avatar = ?
               WHERE name = ?""",
            (personality, speech_style, backstory, json.dumps(sample_lines or []),
             json.dumps(relationships or {}), json.dumps(triggers or []),
             interrupt_tendency, assertiveness, world_context, show or "Custom", avatar or "", name)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_character(name):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM characters WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0
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


def set_session_characters(session_id, character_names):
    """Scopes a session to a specific subset of characters. An empty list is
    treated the same as never calling this at all - see get_session_characters."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM session_characters WHERE session_id = ?", (session_id,))
        for name in character_names:
            cursor.execute(
                """INSERT INTO session_characters (session_id, character_id)
                   SELECT ?, id FROM characters WHERE name = ?""",
                (session_id, name)
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_session_characters(session_id):
    """Returns this session's chosen cast, or every character if none was
    ever chosen (covers sessions from before this feature existed)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM session_characters WHERE session_id = ?", (session_id,)
    )
    has_scoped_roster = cursor.fetchone()[0] > 0

    if not has_scoped_roster:
        cursor.execute("SELECT * FROM characters")
    else:
        cursor.execute("""
            SELECT characters.* FROM characters
            JOIN session_characters ON session_characters.character_id = characters.id
            WHERE session_characters.session_id = ?
            ORDER BY characters.id
        """, (session_id,))

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


def get_last_session():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_session(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_sessions():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sessions.*, COUNT(messages.id) AS message_count
        FROM sessions
        LEFT JOIN messages ON messages.session_id = sessions.id
        GROUP BY sessions.id
        ORDER BY sessions.id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def rename_session(session_id, name):
    """Returns True if a session with that id was actually renamed, False
    if no session had that id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET name = ? WHERE id = ?", (name, session_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_session(session_id):
    """Deletes a conversation entirely - its messages, its character roster
    scoping, and the session itself. Returns True if a session with that id
    actually existed, False otherwise."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM session_characters WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
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