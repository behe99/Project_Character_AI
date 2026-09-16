from flask import Flask, jsonify, request, render_template

from database import (
    init_db, get_all_characters, get_last_session, create_session, get_messages,
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


@app.route("/api/session")
def api_session():
    session_id = get_or_create_session_id()
    messages = get_messages(session_id)
    return jsonify({
        "session_id": session_id,
        "messages": [{"sender": m["sender"], "content": m["content"]} for m in messages],
    })


@app.route("/api/session/new", methods=["POST"])
def api_new_session():
    session_id = create_session("Chat Session")
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
