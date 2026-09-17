import json
import sqlite3

import pytest

from conftest import ONE_CHARACTER


def test_add_and_get_character(db):
    db.add_character(**ONE_CHARACTER)

    characters = db.get_all_characters()
    assert len(characters) == 1
    assert characters[0]["name"] == "Test Character"
    assert json.loads(characters[0]["sample_lines"]) == ["Test line one.", "Test line two."]
    assert json.loads(characters[0]["relationships"]) == {"Other Character": "knows them"}
    assert json.loads(characters[0]["triggers"]) == ["testing"]


def test_add_duplicate_character_raises_integrity_error(db):
    db.add_character(**ONE_CHARACTER)
    with pytest.raises(sqlite3.IntegrityError):
        db.add_character(**ONE_CHARACTER)


def test_delete_character_removes_it_and_returns_true(db):
    db.add_character(**ONE_CHARACTER)
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**other)

    assert db.delete_character("Test Character") is True
    assert {c["name"] for c in db.get_all_characters()} == {"Other Character"}


def test_delete_character_returns_false_when_not_found(db):
    assert db.delete_character("Nobody") is False


def test_failed_insert_does_not_lock_the_database(db):
    """Exercises the exact sequence seed_characters.py runs when a character
    already exists (failed INSERT, then UPDATE in the except branch, then
    another INSERT). This used to fail with "database is locked" without
    conn.rollback() before conn.close() - but that turned out to be a
    timing-sensitive race (100% reproducible as a standalone script, but not
    inside pytest's faster execution), so this test verifies the sequence
    behaves correctly, not that it would have deterministically caught the
    original regression."""
    db.add_character(**ONE_CHARACTER)
    with pytest.raises(sqlite3.IntegrityError):
        db.add_character(**ONE_CHARACTER)

    updated = dict(ONE_CHARACTER, personality="updated personality")
    db.update_character(**updated)  # must not raise "database is locked"

    other = dict(ONE_CHARACTER, name="Second Character")
    db.add_character(**other)  # must not raise "database is locked" either

    assert {c["name"] for c in db.get_all_characters()} == {
        "Test Character", "Second Character"
    }


def test_update_character_overwrites_every_field(db):
    db.add_character(**ONE_CHARACTER)

    updated = dict(
        ONE_CHARACTER,
        personality="A completely different personality.",
        speech_style="Now speaks differently.",
        sample_lines=["New line."],
        triggers=["new-trigger"],
        assertiveness="high",
    )
    db.update_character(**updated)

    characters = db.get_all_characters()
    assert len(characters) == 1
    row = characters[0]
    assert row["personality"] == "A completely different personality."
    assert row["speech_style"] == "Now speaks differently."
    assert json.loads(row["sample_lines"]) == ["New line."]
    assert json.loads(row["triggers"]) == ["new-trigger"]
    assert row["assertiveness"] == "high"


def test_add_character_defaults_show_to_custom(db):
    db.add_character(**ONE_CHARACTER)
    assert db.get_all_characters()[0]["show"] == "Custom"


def test_add_and_update_character_store_show(db):
    db.add_character(**dict(ONE_CHARACTER, show="Vikings"))
    assert db.get_all_characters()[0]["show"] == "Vikings"

    db.update_character(**dict(ONE_CHARACTER, show="The Walking Dead"))
    assert db.get_all_characters()[0]["show"] == "The Walking Dead"


def test_migration_adds_show_to_old_schema(tmp_path, monkeypatch):
    db_path = str(tmp_path / "old_schema_show.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE characters (
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
            world_context TEXT DEFAULT ''
        )
    """)
    conn.execute(
        "INSERT INTO characters (name, personality, speech_style) VALUES (?, ?, ?)",
        ("Old Character", "old personality", "old style"),
    )
    conn.commit()
    conn.close()

    import database
    monkeypatch.setattr(database, "DB_NAME", db_path)
    database.init_db()

    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(characters)")}
    assert "show" in columns
    row = conn.execute("SELECT show FROM characters WHERE name = 'Old Character'").fetchone()
    assert row == ("Custom",)
    conn.close()


def test_migration_adds_backstory_and_sample_lines_to_old_schema(tmp_path, monkeypatch):
    db_path = str(tmp_path / "old_schema.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            personality TEXT NOT NULL,
            speech_style TEXT NOT NULL,
            relationships TEXT DEFAULT '{}',
            triggers TEXT DEFAULT '[]',
            interrupt_tendency TEXT DEFAULT 'medium',
            assertiveness TEXT DEFAULT 'medium'
        )
    """)
    conn.execute(
        "INSERT INTO characters (name, personality, speech_style) VALUES (?, ?, ?)",
        ("Old Character", "old personality", "old style"),
    )
    conn.commit()
    conn.close()

    import database
    monkeypatch.setattr(database, "DB_NAME", db_path)
    database.init_db()

    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(characters)")}
    assert "backstory" in columns
    assert "sample_lines" in columns

    row = conn.execute(
        "SELECT backstory, sample_lines FROM characters WHERE name = 'Old Character'"
    ).fetchone()
    assert row == ("", "[]")
    conn.close()


def test_sessions_and_messages(db):
    session_id = db.create_session("My Session")
    assert db.get_messages(session_id) == []

    db.add_message(session_id, "user", "hello")
    db.add_message(session_id, "Test Character", "hi there")

    messages = db.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["sender"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["sender"] == "Test Character"


def test_get_last_message_id_returns_the_most_recent(db):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "first")
    db.add_message(session_id, "Test Character", "second")

    last_id = db.get_last_message_id(session_id)
    messages = db.get_messages(session_id)
    assert last_id == messages[-1]["id"]
    assert messages[-1]["content"] == "second"


def test_get_last_message_id_returns_none_when_empty(db):
    session_id = db.create_session("s")
    assert db.get_last_message_id(session_id) is None


def test_get_last_message_id_is_scoped_to_its_session(db):
    session_a = db.create_session("a")
    session_b = db.create_session("b")
    db.add_message(session_a, "user", "in session a")

    assert db.get_last_message_id(session_b) is None


def test_delete_message_removes_it_and_returns_true(db):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "keep me")
    db.add_message(session_id, "user", "delete me")
    to_delete = db.get_messages(session_id)[1]["id"]

    assert db.delete_message(to_delete) is True

    remaining = db.get_messages(session_id)
    assert len(remaining) == 1
    assert remaining[0]["content"] == "keep me"


def test_delete_message_returns_false_when_not_found(db):
    assert db.delete_message(999) is False


def test_update_message_edits_its_content_and_returns_true(db):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "typo mesage")
    message_id = db.get_messages(session_id)[0]["id"]

    assert db.update_message(message_id, "fixed message") is True

    messages = db.get_messages(session_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "fixed message"


def test_update_message_returns_false_when_not_found(db):
    assert db.update_message(999, "new content") is False


def test_update_message_does_not_affect_other_messages(db):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "first")
    db.add_message(session_id, "user", "second")
    first_id = db.get_messages(session_id)[0]["id"]

    db.update_message(first_id, "edited first")

    messages = db.get_messages(session_id)
    assert messages[0]["content"] == "edited first"
    assert messages[1]["content"] == "second"


def test_get_last_session_returns_none_when_empty(db):
    assert db.get_last_session() is None


def test_get_last_session_returns_most_recent(db):
    first = db.create_session("First")
    second = db.create_session("Second")

    last = db.get_last_session()
    assert last["id"] == second
    assert last["id"] != first


def test_get_all_sessions_includes_message_counts(db):
    s1 = db.create_session("Session One")
    s2 = db.create_session("Session Two")
    db.add_message(s1, "user", "hi")
    db.add_message(s1, "user", "hi again")

    sessions = db.get_all_sessions()
    by_id = {s["id"]: s for s in sessions}
    assert by_id[s1]["message_count"] == 2
    assert by_id[s2]["message_count"] == 0


def test_get_session_characters_defaults_to_everyone_when_unscoped(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))
    session_id = db.create_session("s")

    names = {c["name"] for c in db.get_session_characters(session_id)}
    assert names == {"Test Character", "Other Character"}


def test_set_session_characters_scopes_the_roster(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))
    session_id = db.create_session("s")

    db.set_session_characters(session_id, ["Test Character"])

    names = [c["name"] for c in db.get_session_characters(session_id)]
    assert names == ["Test Character"]


def test_set_session_characters_does_not_affect_other_sessions(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))
    scoped = db.create_session("scoped")
    unscoped = db.create_session("unscoped")

    db.set_session_characters(scoped, ["Test Character"])

    assert [c["name"] for c in db.get_session_characters(scoped)] == ["Test Character"]
    assert {c["name"] for c in db.get_session_characters(unscoped)} == {
        "Test Character", "Other Character"
    }


def test_set_session_characters_with_empty_list_falls_back_to_everyone(db):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    db.set_session_characters(session_id, [])

    names = {c["name"] for c in db.get_session_characters(session_id)}
    assert names == {"Test Character"}
