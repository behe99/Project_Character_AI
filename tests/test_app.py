from conftest import ONE_CHARACTER

import app as flask_app


def client_for(db):
    flask_app.app.config["TESTING"] = True
    return flask_app.app.test_client()


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


def test_api_session_reports_the_scoped_roster(db):
    db.add_character(**ONE_CHARACTER)
    db.add_character(**dict(ONE_CHARACTER, name="Other Character"))
    session_id = db.create_session("s")
    db.set_session_characters(session_id, ["Test Character"])
    client = client_for(db)

    res = client.get("/api/session")
    assert res.get_json()["characters"] == ["Test Character"]


def test_api_message_returns_replies(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    client = client_for(db)

    monkeypatch.setattr(flask_app, "run_conversation_turn",
                         lambda sid, msg: [("Test Character", "a reply")])

    res = client.post("/api/message", json={"session_id": session_id, "message": "hi"})
    assert res.status_code == 200
    assert res.get_json() == {"replies": [{"sender": "Test Character", "content": "a reply"}]}


def test_api_message_requires_session_id_and_message(db):
    client = client_for(db)

    res = client.post("/api/message", json={"message": "hi"})
    assert res.status_code == 400

    res = client.post("/api/message", json={"session_id": 1, "message": ""})
    assert res.status_code == 400


def test_api_message_surfaces_model_failure_as_error_not_500(db, monkeypatch):
    db.add_character(**ONE_CHARACTER)
    session_id = db.create_session("s")
    client = client_for(db)

    def fake_run_conversation_turn(sid, msg):
        raise RuntimeError("model failed after 3 attempts.")

    monkeypatch.setattr(flask_app, "run_conversation_turn", fake_run_conversation_turn)

    res = client.post("/api/message", json={"session_id": session_id, "message": "hi"})
    assert res.status_code == 200
    assert res.get_json() == {"error": "model failed after 3 attempts."}


def test_index_page_loads(db):
    client = client_for(db)
    res = client.get("/")
    assert res.status_code == 200
    assert b"Character AI Chatroom" in res.data
