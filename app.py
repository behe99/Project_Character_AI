import sqlite3

from flask import Flask, jsonify, request, render_template

from database import (
    init_db, get_all_characters, get_session_characters, set_session_characters,
    get_last_session, create_session, get_messages, add_character, delete_character,
)
from seed_characters import seed
from main import run_conversation_turn

app = Flask(__name__)


def ensure_ready():
    init_db()
    if not get_all_characters():
        seed()


def get_or_create_session_id():
    last_session = get_last_session()
    if last_session is not None:
        return last_session["id"]
    return create_session("Chat Session")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/characters")
def api_characters():
    characters = sorted(get_all_characters(), key=lambda c: c["id"])
    return jsonify([
        {"id": c["id"], "name": c["name"], "personality": c["personality"]}
        for c in characters
    ])


@app.route("/api/characters", methods=["POST"])
def api_create_character():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    personality = (data.get("personality") or "").strip()
    speech_style = (data.get("speech_style") or "").strip()
    world_context = (data.get("world_context") or "").strip()

    if not name or not personality or not speech_style or not world_context:
        return jsonify({
            "error": "name, personality, speech_style, and world_context are required"
        }), 400

    try:
        add_character(
            name=name,
            personality=personality,
            speech_style=speech_style,
            world_context=world_context,
            backstory=(data.get("backstory") or "").strip(),
            sample_lines=data.get("sample_lines") or [],
            relationships=data.get("relationships") or {},
            triggers=data.get("triggers") or [],
            interrupt_tendency=data.get("interrupt_tendency") or "medium",
            assertiveness=data.get("assertiveness") or "medium",
        )
    except sqlite3.IntegrityError:
        return jsonify({"error": f"'{name}' already exists"}), 409

    return jsonify({"ok": True}), 201


@app.route("/api/characters/<name>", methods=["DELETE"])
def api_delete_character(name):
    deleted = delete_character(name)
    if not deleted:
        return jsonify({"error": f"'{name}' not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/session")
def api_session():
    session_id = get_or_create_session_id()
    messages = get_messages(session_id)
    characters = sorted(get_session_characters(session_id), key=lambda c: c["id"])
    return jsonify({
        "session_id": session_id,
        "messages": [{"sender": m["sender"], "content": m["content"]} for m in messages],
        "characters": [c["name"] for c in characters],
    })


@app.route("/api/session/new", methods=["POST"])
def api_new_session():
    data = request.get_json(silent=True) or {}
    character_names = data.get("characters")

    session_id = create_session("Chat Session")
    if character_names:
        set_session_characters(session_id, character_names)

    return jsonify({"session_id": session_id})


@app.route("/api/message", methods=["POST"])
def api_message():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    user_message = (data.get("message") or "").strip()

    if not session_id or not user_message:
        return jsonify({"error": "session_id and message are required"}), 400

    try:
        replies = run_conversation_turn(session_id, user_message)
    except (RuntimeError, ValueError) as e:
        return jsonify({"error": str(e)})

    return jsonify({
        "replies": [{"sender": name, "content": reply} for name, reply in replies]
    })


if __name__ == "__main__":
    ensure_ready()
    app.run(debug=True, port=5000)
