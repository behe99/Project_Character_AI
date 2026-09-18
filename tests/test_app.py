import queue
import time

import pytest

from conftest import ONE_CHARACTER

import app as flask_app
import main


def client_for(db):
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


@pytest.fixture(autouse=True)
def _reset_worker_state():
    """app.py tracks queues/subscribers/workers/idle timers in module-level
    dicts keyed by session_id. Each test's `db` fixture starts a fresh
    SQLite file where session ids restart at 1, so without this reset a
    session_id from one test would collide with leftover state (a worker
    already "started", an idle timer already scheduled) from an earlier
    test that happened to use the same id."""
    def _clear():
        flask_app._session_queues.clear()
        flask_app._session_subscribers.clear()
        flask_app._workers_started.clear()
        for timer in flask_app._idle_timers.values():
            timer.cancel()
        flask_app._idle_timers.clear()

    _clear()
    yield
    _clear()


def test_api_characters_lists_roster(db):
    db.add_character(**ONE_CHARACTER)
    client = client_for(db)

    res = client.get("/api/characters")
    assert res.status_code == 200
    names = [c["name"] for c in res.get_json()]
    assert names == ["Test Character"]


def test_api_create_character(db):
    client = client_for(db)

    res = client.post("/api/characters", json={
        "name": "Melisandre",
        "show": "Game of Thrones",
        "personality": "A red priestess obsessed with fire and prophecy.",
        "speech_style": "Mystical, short declarations.",
        "world_context": "Medieval fantasy, no modern technology.",
        "sample_lines": ["The night is dark and full of terrors."],
        "relationships": {"Jon Snow": "brought him back from death"},
        "triggers": ["fire", "prophecy"],
        "interrupt_tendency": "high",
    })
    assert res.status_code == 201

    characters = db.get_all_characters()
    assert len(characters) == 1
    assert characters[0]["name"] == "Melisandre"
    assert characters[0]["show"] == "Game of Thrones"
    assert characters[0]["interrupt_tendency"] == "high"
    assert characters[0]["assertiveness"] == "medium"  # default


def test_api_create_character_without_show_defaults_to_custom(db):
    client = client_for(db)

    res = client.post("/api/characters", json={
        "name": "X", "personality": "p", "speech_style": "s", "world_context": "w",
    })
    assert res.status_code == 201
    assert db.get_all_characters()[0]["show"] == "Custom"


def test_api_characters_includes_show(db):
    db.add_character(**dict(ONE_CHARACTER, show="Vikings"))
    client = client_for(db)

    res = client.get("/api/characters")
    assert res.get_json()[0]["show"] == "Vikings"


def test_api_create_character_requires_core_fields(db):
    client = client_for(db)

    res = client.post("/api/characters", json={"name": "X"})
    assert res.status_code == 400
    assert db.get_all_characters() == []


def test_api_create_character_requires_world_context(db):
    """world_context matters enough (a modern character assuming no phones exist,
    or a fantasy character casually mentioning the internet) that it's required,
    not just nice to have."""
    client = client_for(db)

    res = client.post("/api/characters", json={
        "name": "X", "personality": "p", "speech_style": "s",
    })
    assert res.status_code == 400
    assert db.get_all_characters() == []


def test_api_create_character_rejects_duplicate_name(db):
    db.add_character(**ONE_CHARACTER)
    client = client_for(db)

    res = client.post("/api/characters", json={
        "name": "Test Character",
        "personality": "different",
        "speech_style": "different",
        "world_context": "different",
    })
    assert res.status_code == 409
    assert len(db.get_all_characters()) == 1


def test_api_delete_character(db):
    db.add_character(**ONE_CHARACTER)
    client = client_for(db)

    res = client.delete("/api/characters/Test Character")
    assert res.status_code == 200
    assert db.get_all_characters() == []


def test_api_delete_character_returns_404_when_not_found(db):
    client = client_for(db)

    res = client.delete("/api/characters/Nobody")
    assert res.status_code == 404


def test_api_session_creates_one_when_none_exists(db):
    client = client_for(db)

    res = client.get("/api/session")
    data = res.get_json()
    assert data["messages"] == []
    assert db.get_all_sessions()[0]["id"] == data["session_id"]


def test_api_session_returns_existing_messages(db):
    session_id = db.create_session("Chat Session")
    db.add_message(session_id, "user", "hi")
    client = client_for(db)

    res = client.get("/api/session")
    data = res.get_json()
    assert data["session_id"] == session_id
    assert data["messages"] == [{"sender": "user", "content": "hi"}]


def test_api_new_session_creates_another_session(db):
    first = db.create_session("Chat Session")
    client = client_for(db)

    res = client.post("/api/session/new")
    new_id = res.get_json()["session_id"]
    assert new_id != first
    assert {s["id"] for s in db.get_all_sessions()} == {first, new_id}


def test_api_new_session_with_characters_scopes_the_roster(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))
    client = client_for(db)

    res = client.post("/api/session/new", json={"characters": ["Test Character"]})
    session_id = res.get_json()["session_id"]

    names = [c["name"] for c in db.get_session_characters(session_id)]
    assert names == ["Test Character"]


def test_api_new_session_accepts_a_name(db):
    client = client_for(db)

    res = client.post("/api/session/new", json={"name": "Vikings night"})
    session_id = res.get_json()["session_id"]

    sessions = db.get_all_sessions()
    assert next(s for s in sessions if s["id"] == session_id)["name"] == "Vikings night"


def test_api_new_session_without_a_name_defaults_to_chat_session(db):
    client = client_for(db)

    res = client.post("/api/session/new", json={})
    session_id = res.get_json()["session_id"]

    sessions = db.get_all_sessions()
    assert next(s for s in sessions if s["id"] == session_id)["name"] == "Chat Session"


def test_api_session_by_id_loads_a_specific_past_conversation(db):
    old = db.create_session("Old conversation")
    db.add_message(old, "user", "from the past")
    current = db.create_session("Current")
    db.add_message(current, "user", "right now")
    client = client_for(db)

    res = client.get(f"/api/session/{old}")
    data = res.get_json()
    assert data["session_id"] == old
    assert data["messages"] == [{"sender": "user", "content": "from the past"}]


def test_api_sessions_lists_most_recent_first(db):
    first = db.create_session("First")
    second = db.create_session("Second")
    db.add_message(first, "user", "hi")
    client = client_for(db)

    res = client.get("/api/sessions")
    data = res.get_json()
    assert [s["id"] for s in data] == [second, first]
    assert next(s for s in data if s["id"] == first)["message_count"] == 1


def test_api_rename_session(db):
    session_id = db.create_session("Chat Session")
    client = client_for(db)

    res = client.put(f"/api/sessions/{session_id}", json={"name": "Vikings night"})
    assert res.status_code == 200
    assert db.get_all_sessions()[0]["name"] == "Vikings night"


def test_api_rename_session_requires_a_name(db):
    session_id = db.create_session("Chat Session")
    client = client_for(db)

    res = client.put(f"/api/sessions/{session_id}", json={"name": "  "})
    assert res.status_code == 400
    assert db.get_all_sessions()[0]["name"] == "Chat Session"


def test_api_rename_session_returns_404_when_not_found(db):
    client = client_for(db)

    res = client.put("/api/sessions/999", json={"name": "Anything"})
    assert res.status_code == 404


def test_api_delete_session(db):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello")
    client = client_for(db)

    res = client.delete(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    assert db.get_all_sessions() == []


def test_api_delete_session_returns_404_when_not_found(db):
    client = client_for(db)

    res = client.delete("/api/sessions/999")
    assert res.status_code == 404


def test_api_session_reports_the_scoped_roster(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))
    session_id = db.create_session("s")
    db.set_session_characters(session_id, ["Test Character"])
    client = client_for(db)

    res = client.get("/api/session")
    assert res.get_json()["characters"] == ["Test Character"]


def test_api_message_requires_session_id_and_message(db):
    client = client_for(db)

    res = client.post("/api/message", json={"message": "hi"})
    assert res.status_code == 400

    res = client.post("/api/message", json={"session_id": 1, "message": ""})
    assert res.status_code == 400


def test_api_message_queues_instead_of_blocking(db, monkeypatch):
    """/api/message hands the message to a background worker and returns
    immediately - replies arrive later over /api/stream, not in this
    response - so sending a second message never has to wait for the first
    round to finish generating."""
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    client = client_for(db)

    call_count = {"n": 0}

    def fake_decide_speakers(session_id, latest_message, exclude=None, turns_so_far=0):
        call_count["n"] += 1
        return ["Test Character"] if call_count["n"] == 1 else []

    monkeypatch.setattr(main, "decide_speakers", fake_decide_speakers)
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    # Subscribe before posting so we don't miss the broadcast.
    subscriber = flask_app._subscribe(session_id)

    res = client.post("/api/message", json={"session_id": session_id, "message": "hi"})
    assert res.status_code == 202
    assert res.get_json() == {"queued": True}

    # The real background worker thread processes the queue asynchronously;
    # poll briefly instead of assuming it already ran by the time we check.
    deadline = time.time() + 2
    events = []
    while time.time() < deadline and not any(e.get("type") == "round_done" for e in events):
        try:
            events.append(subscriber.get(timeout=0.05))
        except queue.Empty:
            pass

    # The user's own message is written to the DB by the worker itself, once
    # it actually starts processing - not by the request thread.
    assert [m["sender"] for m in db.get_messages(session_id)] == ["user"]

    reply_events = [e for e in events if e["type"] == "reply"]
    assert reply_events == [
        {"type": "reply", "sender": "Test Character", "content": "a reply"}
    ]


def test_process_one_item_broadcasts_replies_then_round_done(db, monkeypatch):
    """_process_one_item is the synchronous unit the worker thread calls per
    queued item - tested directly (no thread, no timing) so the broadcast
    sequence is deterministic."""
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    call_count = {"n": 0}

    def fake_decide_speakers(session_id, latest_message, exclude=None, turns_so_far=0):
        call_count["n"] += 1
        return ["Test Character"] if call_count["n"] == 1 else []

    monkeypatch.setattr(main, "decide_speakers", fake_decide_speakers)
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "a reply")

    subscriber = flask_app._subscribe(session_id)
    flask_app._process_one_item(session_id, ("user", "hi"))
    flask_app._cancel_idle_check(session_id)

    events = []
    while not subscriber.empty():
        events.append(subscriber.get_nowait())

    assert events == [
        {"type": "speaker_picked", "sender": "Test Character"},
        {"type": "reply", "sender": "Test Character", "content": "a reply"},
        {"type": "round_done"},
    ]


def test_process_one_item_broadcasts_error_on_failure(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")

    def failing_reply(sid, name):
        raise RuntimeError("model failed after 3 attempts.")

    monkeypatch.setattr(main, "decide_speakers", lambda *a, **k: ["Test Character"])
    monkeypatch.setattr(main, "generate_character_reply", failing_reply)

    subscriber = flask_app._subscribe(session_id)
    flask_app._process_one_item(session_id, ("user", "hi"))
    flask_app._cancel_idle_check(session_id)

    events = []
    while not subscriber.empty():
        events.append(subscriber.get_nowait())

    assert events == [
        {"type": "speaker_picked", "sender": "Test Character"},
        {"type": "error", "message": "model failed after 3 attempts."},
        {"type": "round_done"},
    ]


def test_process_one_item_runs_an_idle_turn(db, monkeypatch):
    """An ("idle", None) item runs run_idle_turn_stream instead of a user
    round - this is what a fired idle timer enqueues."""
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    monkeypatch.setattr(main, "decide_idle_speaker", lambda sid: "Test Character")
    monkeypatch.setattr(main, "generate_character_reply", lambda sid, name: "spontaneous line")

    subscriber = flask_app._subscribe(session_id)
    flask_app._process_one_item(session_id, ("idle", None))
    flask_app._cancel_idle_check(session_id)

    events = []
    while not subscriber.empty():
        events.append(subscriber.get_nowait())

    assert events == [
        {"type": "speaker_picked", "sender": "Test Character"},
        {"type": "reply", "sender": "Test Character", "content": "spontaneous line"},
        {"type": "round_done"},
    ]


def test_process_one_item_idle_turn_yields_nothing_when_nobody_speaks(db, monkeypatch):
    session_id = db.create_session("s")
    db.add_message(session_id, "user", "hello?")

    monkeypatch.setattr(main, "decide_idle_speaker", lambda sid: None)

    subscriber = flask_app._subscribe(session_id)
    flask_app._process_one_item(session_id, ("idle", None))
    flask_app._cancel_idle_check(session_id)

    events = []
    while not subscriber.empty():
        events.append(subscriber.get_nowait())

    assert events == [{"type": "round_done"}]


def test_unsubscribe_stops_further_broadcasts(db):
    session_id = db.create_session("s")
    subscriber = flask_app._subscribe(session_id)

    flask_app._broadcast(session_id, {"type": "reply", "sender": "X", "content": "one"})
    flask_app._unsubscribe(session_id, subscriber)
    flask_app._broadcast(session_id, {"type": "reply", "sender": "X", "content": "two"})

    events = []
    while not subscriber.empty():
        events.append(subscriber.get_nowait())

    assert events == [{"type": "reply", "sender": "X", "content": "one"}]


def test_unsubscribe_last_subscriber_cancels_idle_check(db):
    session_id = db.create_session("s")
    subscriber = flask_app._subscribe(session_id)
    flask_app._schedule_idle_check(session_id)
    assert session_id in flask_app._idle_timers

    flask_app._unsubscribe(session_id, subscriber)
    assert session_id not in flask_app._idle_timers


def test_subscribe_schedules_idle_check_only_for_active_sessions(db):
    """A session with no worker yet (nothing has ever been sent) shouldn't
    get idle chatter scheduled just because someone opened the page."""
    fresh_session_id = db.create_session("fresh")
    flask_app._subscribe(fresh_session_id)
    assert fresh_session_id not in flask_app._idle_timers

    active_session_id = db.create_session("active")
    with flask_app._lock:
        flask_app._workers_started.add(active_session_id)
    flask_app._subscribe(active_session_id)
    assert active_session_id in flask_app._idle_timers
    flask_app._cancel_idle_check(active_session_id)


def test_index_page_loads(db):
    client = client_for(db)
    res = client.get("/")
    assert res.status_code == 200
    assert b"Character AI Chatroom" in res.data
