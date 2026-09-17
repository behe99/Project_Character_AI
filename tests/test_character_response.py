import pytest

from conftest import ONE_CHARACTER

import character_response as cr


def test_raises_for_unknown_character(db):
    session_id = db.create_session("s")
    with pytest.raises(ValueError):
        cr.generate_character_reply(session_id, "Nobody")


def test_reply_is_saved_to_the_conversation(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello")

    monkeypatch.setattr(cr, "call_model", lambda prompt: "Hi there.")

    reply = cr.generate_character_reply(session_id, "Test Character")
    assert reply == "Hi there."

    messages = db.get_messages(session_id)
    assert messages[-1]["sender"] == "Test Character"
    assert messages[-1]["content"] == "Hi there."


def test_prompt_includes_backstory_and_sample_lines(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello")

    captured = {}

    def fake_call_model(prompt):
        captured["prompt"] = prompt
        return "reply"

    monkeypatch.setattr(cr, "call_model", fake_call_model)
    cr.generate_character_reply(session_id, "Test Character")

    assert "A test backstory." in captured["prompt"]
    assert "Test line one." in captured["prompt"]
    assert "Test line two." in captured["prompt"]
    assert "testing" in captured["prompt"]
    assert "A test world with no special rules." in captured["prompt"]


def test_generate_replies_for_speakers_returns_in_order(db, monkeypatch):
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello")

    monkeypatch.setattr(cr, "call_model", lambda prompt: "reply")

    results = cr.generate_replies_for_speakers(
        session_id, ["Test Character", "Other Character"]
    )
    assert [name for name, _ in results] == ["Test Character", "Other Character"]
