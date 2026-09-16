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
