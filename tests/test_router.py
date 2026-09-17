from conftest import ONE_CHARACTER

import router


def test_filters_out_hallucinated_character_names(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(
        router, "call_model",
        lambda prompt: '{"speakers": ["Test Character", "Made Up Character"]}'
    )

    speakers = router.decide_speakers(session_id, "hello")
    assert speakers == ["Test Character"]


def test_excludes_the_given_speaker(db, monkeypatch):
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")

    monkeypatch.setattr(
        router, "call_model",
        lambda prompt: '{"speakers": ["Test Character", "Other Character"]}'
    )

    speakers = router.decide_speakers(session_id, "hello", exclude="Test Character")
    assert speakers == ["Other Character"]


def test_invalid_json_returns_empty_list(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(router, "call_model", lambda prompt: "not json at all")

    assert router.decide_speakers(session_id, "hello") == []


def test_strips_markdown_code_fences_before_parsing(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(
        router, "call_model",
        lambda prompt: '```json\n{"speakers": ["Test Character"]}\n```'
    )

    assert router.decide_speakers(session_id, "hello") == ["Test Character"]


def test_missing_speakers_key_returns_empty_list(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(router, "call_model", lambda prompt: '{"something_else": []}')

    assert router.decide_speakers(session_id, "hello") == []


def test_filters_out_characters_outside_the_session_roster(db, monkeypatch):
    """A character who exists globally but isn't part of THIS session's
    chosen cast should be filtered out just like a hallucinated name."""
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")
    db.set_session_characters(session_id, ["Test Character"])

    monkeypatch.setattr(
        router, "call_model",
        lambda prompt: '{"speakers": ["Test Character", "Other Character"]}'
    )

    speakers = router.decide_speakers(session_id, "hello")
    assert speakers == ["Test Character"]


def test_decide_speakers_prompt_notes_first_turn_by_default(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    captured = {}

    def fake_call_model(prompt):
        captured["prompt"] = prompt
        return '{"speakers": []}'

    monkeypatch.setattr(router, "call_model", fake_call_model)
    router.decide_speakers(session_id, "hello")

    assert "FIRST reply" in captured["prompt"]


def test_decide_speakers_prompt_escalates_pressure_on_later_turns(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    captured = {}

    def fake_call_model(prompt):
        captured["prompt"] = prompt
        return '{"speakers": []}'

    monkeypatch.setattr(router, "call_model", fake_call_model)
    router.decide_speakers(session_id, "hello", turns_so_far=2)

    assert "2 character(s) have already replied" in captured["prompt"]
    assert "FIRST reply" not in captured["prompt"]


def test_decide_idle_speaker_returns_the_picked_name(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    monkeypatch.setattr(
        router, "call_model", lambda prompt: '{"speaker": "Test Character"}'
    )

    assert router.decide_idle_speaker(session_id) == "Test Character"


def test_decide_idle_speaker_returns_none_when_nobody_speaks_up(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    monkeypatch.setattr(router, "call_model", lambda prompt: '{"speaker": null}')

    assert router.decide_idle_speaker(session_id) is None


def test_decide_idle_speaker_ignores_a_hallucinated_name(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    monkeypatch.setattr(
        router, "call_model", lambda prompt: '{"speaker": "Made Up Character"}'
    )

    assert router.decide_idle_speaker(session_id) is None


def test_decide_idle_speaker_returns_none_on_invalid_json(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    monkeypatch.setattr(router, "call_model", lambda prompt: "not json at all")

    assert router.decide_idle_speaker(session_id) is None


def test_decide_idle_speaker_returns_none_with_no_messages_yet(db):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    assert router.decide_idle_speaker(session_id) is None


def test_decide_idle_speaker_returns_none_with_no_characters(db):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    assert router.decide_idle_speaker(session_id) is None
