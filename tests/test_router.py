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
