from conftest import ONE_CHARACTER

import main


def test_guarantees_at_least_one_reply_on_first_round(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(main, "decide_speakers", lambda *a, **k: [])
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    replies = main.run_conversation_turn(session_id, "hello")

    assert [name for name, _ in replies] == ["Test Character"]


def test_run_idle_turn_stream_yields_the_picked_speaker(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(main, "decide_idle_speaker", lambda sid: "Test Character")
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "spontaneous line")

    replies = list(main.run_idle_turn_stream(session_id))

    assert replies == [("Test Character", "spontaneous line")]


def test_run_idle_turn_stream_yields_nothing_when_nobody_speaks_up(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    monkeypatch.setattr(main, "decide_idle_speaker", lambda sid: None)

    assert list(main.run_idle_turn_stream(session_id)) == []


def test_run_idle_turn_stream_calls_on_speaker_picked_before_generating(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    picked = []
    monkeypatch.setattr(main, "decide_idle_speaker", lambda sid: "Test Character")

    def fake_generate_character_reply(sid, name):
        assert picked == ["Test Character"]  # picked before the (slow) generation
        return "spontaneous line"

    monkeypatch.setattr(main, "generate_character_reply", fake_generate_character_reply)

    list(main.run_idle_turn_stream(session_id, on_speaker_picked=picked.append))

    assert picked == ["Test Character"]


def test_run_idle_turn_stream_does_not_call_on_speaker_picked_when_nobody_speaks(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    picked = []
    monkeypatch.setattr(main, "decide_idle_speaker", lambda sid: None)

    list(main.run_idle_turn_stream(session_id, on_speaker_picked=picked.append))

    assert picked == []


def test_run_conversation_turn_stream_calls_on_speaker_picked_for_each_turn(db, monkeypatch):
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")

    call_count = {"n": 0}

    def fake_decide_speakers(session_id, latest_message, exclude=None):
        call_count["n"] += 1
        return ["Test Character", "Other Character"] if call_count["n"] == 1 else []

    monkeypatch.setattr(main, "decide_speakers", fake_decide_speakers)
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    picked = []
    list(main.run_conversation_turn_stream(session_id, "hello", on_speaker_picked=picked.append))

    assert picked == ["Test Character", "Other Character"]


def test_run_conversation_turn_stream_yields_before_the_round_finishes(db, monkeypatch):
    """The whole point of the streaming version is that a caller can act on
    the first reply without waiting for the rest - verified here by reading
    only one item from the generator and confirming the second reply hasn't
    been generated yet."""
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")

    generated = []

    def fake_generate_character_reply(sid, name):
        generated.append(name)
        return "a reply"

    monkeypatch.setattr(
        main, "decide_speakers",
        lambda *a, **k: ["Test Character", "Other Character"]
    )
    monkeypatch.setattr(main, "generate_character_reply", fake_generate_character_reply)

    gen = main.run_conversation_turn_stream(session_id, "hello")
    first = next(gen)

    assert first == ("Test Character", "a reply")
    assert generated == ["Test Character"]  # the second reply isn't generated yet

    second = next(gen)
    assert second == ("Other Character", "a reply")


def test_no_fallback_reply_on_later_rounds(db, monkeypatch):
    """The guaranteed-reply fallback only applies to the user's own message,
    not to character-to-character rounds that legitimately end at 0."""
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    call_count = {"n": 0}

    def fake_decide_speakers(session_id, latest_message, exclude=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return ["Test Character"]
        return []

    monkeypatch.setattr(main, "decide_speakers", fake_decide_speakers)
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    replies = main.run_conversation_turn(session_id, "hello")

    assert [name for name, _ in replies] == ["Test Character"]


def test_turn_cap_holds_even_if_router_never_stops(db, monkeypatch):
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")

    monkeypatch.setattr(
        main, "decide_speakers",
        lambda *a, **k: ["Test Character", "Other Character"]
    )
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    replies = main.run_conversation_turn(session_id, "hello")

    assert len(replies) == main.MAX_CHARACTER_TURNS_PER_MESSAGE


def test_fallback_reply_only_picks_from_the_session_roster(db, monkeypatch):
    other = dict(ONE_CHARACTER, name="Other Character")
    db.add_character(**ONE_CHARACTER)
    db.add_character(**other)
    session_id = db.create_session("s")
    db.set_session_characters(session_id, ["Test Character"])

    monkeypatch.setattr(main, "decide_speakers", lambda *a, **k: [])
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    replies = main.run_conversation_turn(session_id, "hello")

    assert [name for name, _ in replies] == ["Test Character"]


def test_choose_characters_cli_parses_selected_numbers(db, monkeypatch, capsys):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))

    monkeypatch.setattr("builtins.input", lambda prompt="": "2")

    assert main.choose_characters_cli() == ["Other Character"]


def test_choose_characters_cli_blank_input_means_everyone(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))

    monkeypatch.setattr("builtins.input", lambda prompt="": "")

    assert set(main.choose_characters_cli()) == {"Test Character", "Other Character"}


def test_choose_characters_cli_garbage_input_means_everyone(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)

    monkeypatch.setattr("builtins.input", lambda prompt="": "not a number")

    assert main.choose_characters_cli() == ["Test Character"]


def test_choose_characters_cli_accepts_a_show_name(db, monkeypatch):
    db.add_character(**dict(ONE_CHARACTER, name="Ragnar", show="Vikings"))
    db.add_character(**dict(ONE_CHARACTER, name="Lagertha", show="Vikings"))
    db.add_character(**dict(ONE_CHARACTER, name="Rick", show="The Walking Dead"))

    monkeypatch.setattr("builtins.input", lambda prompt="": "Vikings")

    assert set(main.choose_characters_cli()) == {"Ragnar", "Lagertha"}


def test_group_by_show_orders_known_shows_first(db):
    db.add_character(**dict(ONE_CHARACTER, name="Rick", show="The Walking Dead"))
    db.add_character(**dict(ONE_CHARACTER, name="Homemade Hero", show="Custom"))
    db.add_character(**dict(ONE_CHARACTER, name="Tyrion", show="Game of Thrones"))

    characters = sorted(db.get_all_characters(), key=lambda c: c["id"])
    shows = [show for show, _ in main.group_by_show(characters)]

    assert shows.index("Game of Thrones") < shows.index("The Walking Dead")
    assert "Custom" in shows


def test_start_new_session_cli_scopes_the_new_session(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))

    monkeypatch.setattr("builtins.input", lambda prompt="": "1")

    session_id = main.start_new_session_cli()

    assert [c["name"] for c in db.get_session_characters(session_id)] == ["Test Character"]


def test_list_characters_prints_each_name(db, capsys):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))

    color_map = main.build_color_map()
    main.list_characters(color_map)

    out = capsys.readouterr().out
    assert "Test Character" in out
    assert "Other Character" in out


def test_list_characters_handles_empty_roster(db, capsys):
    main.list_characters({})
    assert "No characters in the roster." in capsys.readouterr().out


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
