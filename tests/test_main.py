from conftest import ONE_CHARACTER

import main


def test_guarantees_at_least_one_reply_on_first_round(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    calls = []

    monkeypatch.setattr(main, "decide_speakers", lambda *a, **k: [])
    monkeypatch.setattr(
        main, "generate_character_reply",
        lambda sid, name: calls.append(name) or "a reply"
    )

    color_map = main.build_color_map()
    main.run_conversation_turn(session_id, "hello", color_map)

    assert calls == ["Test Character"]


def test_no_fallback_reply_on_later_rounds(db, monkeypatch):
    """The guaranteed-reply fallback only applies to the user's own message,
    not to character-to-character rounds that legitimately end at 0."""
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    calls = []

    call_count = {"n": 0}

    def fake_decide_speakers(session_id, latest_message, exclude=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ["Test Character"]
        return []

    monkeypatch.setattr(main, "decide_speakers", fake_decide_speakers)
    monkeypatch.setattr(
        main, "generate_character_reply",
        lambda sid, name: calls.append(name) or "a reply"
    )

    color_map = main.build_color_map()
    main.run_conversation_turn(session_id, "hello", color_map)

    assert calls == ["Test Character"]


def test_turn_cap_holds_even_if_router_never_stops(db, monkeypatch):
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")
    calls = []

    monkeypatch.setattr(
        main, "decide_speakers",
        lambda *a, **k: ["Test Character", "Other Character"]
    )
    monkeypatch.setattr(
        main, "generate_character_reply",
        lambda sid, name: calls.append(name) or "a reply"
    )

    color_map = main.build_color_map()
    main.run_conversation_turn(session_id, "hello", color_map)

    assert len(calls) == main.MAX_CHARACTER_TURNS_PER_MESSAGE


def test_build_color_map_assigns_one_color_per_character(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))

    color_map = main.build_color_map()
    assert set(color_map.keys()) == {"Test Character", "Other Character"}
    assert color_map["Test Character"] != color_map["Other Character"]


def test_resume_or_create_session_starts_fresh_when_none_exists(db):
    color_map = {}
    session_id = main.resume_or_create_session(color_map)
    assert db.get_all_sessions()[0]["id"] == session_id


def test_resume_or_create_session_resumes_existing(db, capsys):
    existing = db.create_session("Chat Session")
    db.add_message(existing, "user", "hello")

    color_map = {}
    session_id = main.resume_or_create_session(color_map)

    assert session_id == existing
    assert "Resuming previous conversation" in capsys.readouterr().out
