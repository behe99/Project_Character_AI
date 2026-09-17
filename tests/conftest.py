import os
import sys

# llm.py reads GEMINI_API_KEY at import time - set a dummy one before any
# test imports the app modules, so tests never need a real API key.
os.environ.setdefault("GEMINI_API_KEY", "test-key-for-pytest")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Points database.py at a fresh temp SQLite file for the duration of one test."""
    db_path = str(tmp_path / "test_chatroom.db")
    monkeypatch.setattr(database, "DB_NAME", db_path)
    database.init_db()
    return database


ONE_CHARACTER = dict(
    name="Test Character",
    personality="A test personality.",
    speech_style="Speaks in short test sentences.",
    world_context="A test world with no special rules.",
    backstory="A test backstory.",
    sample_lines=["Test line one.", "Test line two."],
    relationships={"Other Character": "knows them"},
    triggers=["testing"],
    interrupt_tendency="medium",
    assertiveness="medium",
)
