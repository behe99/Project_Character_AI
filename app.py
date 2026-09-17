import json
import queue
import random
import sqlite3
import threading

from flask import Flask, jsonify, request, render_template, Response, stream_with_context

from database import (
    init_db, get_all_characters, get_session_characters, set_session_characters,
    get_last_session, create_session, get_messages, add_character, delete_character,
    delete_message, update_message, get_all_sessions, rename_session, delete_session,
)
from seed_characters import seed
import main

app = Flask(__name__)

# Each session gets its own FIFO queue of pending work items and its own
# background worker thread that processes them one at a time. This is what
# lets someone send a second message while characters are still replying to
# the first: it's queued immediately (and shown in their own browser right
# away) instead of blocking, but the worker only starts generating replies
# for it once the in-progress round has fully finished - so an interruption
# never garbles a round that's already underway. Every reply the worker
# generates is pushed to that session's subscribers (open /api/stream
# connections) as soon as it's ready, so the browser can render them one by
# one instead of waiting for the whole round.
#
# A queue item is ("user", message_text) for something the user sent, or
# ("idle", None) for a scheduled check of whether a character should speak
# up unprompted after a period of silence (see the idle-timer functions
# below). Both kinds go through the same queue so they're never processed
# out of order or on top of each other.
_lock = threading.Lock()
_session_queues = {}
_session_subscribers = {}
_workers_started = set()
_idle_timers = {}

# How long a session has to sit quiet, with someone actually watching it,
# before a character might speak up on their own. Randomized so it doesn't
# feel like a mechanical timer going off on the dot.
IDLE_MIN_SECONDS = 60
IDLE_MAX_SECONDS = 180


def _get_queue(session_id):
    with _lock:
        if session_id not in _session_queues:
            _session_queues[session_id] = queue.Queue()
        return _session_queues[session_id]


def _broadcast(session_id, event):
    with _lock:
        subscribers = list(_session_subscribers.get(session_id, []))
    for subscriber_queue in subscribers:
        subscriber_queue.put(event)


def _subscribe(session_id):
    subscriber_queue = queue.Queue()
    with _lock:
        _session_subscribers.setdefault(session_id, []).append(subscriber_queue)
    # Only worth scheduling idle chatter once there's a real conversation
    # (a worker has processed at least one message) and someone's watching.
    if session_id in _workers_started:
        _schedule_idle_check(session_id)
    return subscriber_queue


def _unsubscribe(session_id, subscriber_queue):
    with _lock:
        subscribers = _session_subscribers.get(session_id, [])
        if subscriber_queue in subscribers:
            subscribers.remove(subscriber_queue)
        still_watched = len(subscribers) > 0
    if not still_watched:
        _cancel_idle_check(session_id)


def _schedule_idle_check(session_id):
    _cancel_idle_check(session_id)
    delay = random.uniform(IDLE_MIN_SECONDS, IDLE_MAX_SECONDS)
    timer = threading.Timer(delay, _trigger_idle_check, args=(session_id,))
    timer.daemon = True
    with _lock:
        _idle_timers[session_id] = timer
    timer.start()


def _cancel_idle_check(session_id):
    with _lock:
        timer = _idle_timers.pop(session_id, None)
    if timer:
        timer.cancel()


def _trigger_idle_check(session_id):
    _get_queue(session_id).put(("idle", None))


def _process_one_item(session_id, item):
    kind, payload = item
    saved_ids = {}

    def on_speaker_picked(name):
        _broadcast(session_id, {"type": "speaker_picked", "sender": name})

    def on_message_saved(sender, message_id):
        if sender == "user":
            _broadcast(session_id, {"type": "user_message_saved", "id": message_id})
        else:
            saved_ids[sender] = message_id

    try:
        if kind == "user":
            stream = main.run_conversation_turn_stream(
                session_id, payload,
                on_speaker_picked=on_speaker_picked, on_message_saved=on_message_saved,
            )
        else:
            stream = main.run_idle_turn_stream(
                session_id,
                on_speaker_picked=on_speaker_picked, on_message_saved=on_message_saved,
            )
        for name, reply in stream:
            _broadcast(session_id, {
                "type": "reply", "sender": name, "content": reply, "id": saved_ids.get(name),
            })
    except (RuntimeError, ValueError) as e:
        _broadcast(session_id, {"type": "error", "message": str(e)})
    _broadcast(session_id, {"type": "round_done"})

    # Only worth rescheduling if someone's still actually watching.
    with _lock:
        still_watched = bool(_session_subscribers.get(session_id))
    if still_watched:
        _schedule_idle_check(session_id)


def _worker_loop(session_id):
    session_queue = _get_queue(session_id)
    while True:
        item = session_queue.get()
        _process_one_item(session_id, item)


def _ensure_worker(session_id):
    with _lock:
        if session_id in _workers_started:
            return
        _workers_started.add(session_id)
    thread = threading.Thread(target=_worker_loop, args=(session_id,), daemon=True)
    thread.start()


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
        {
            "id": c["id"],
            "name": c["name"],
            "personality": c["personality"],
            "show": c["show"] or "Custom",
        }
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
            show=(data.get("show") or "Custom").strip() or "Custom",
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


@app.route("/api/messages/<int:message_id>", methods=["DELETE"])
def api_delete_message(message_id):
    deleted = delete_message(message_id)
    if not deleted:
        return jsonify({"error": "message not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/messages/<int:message_id>", methods=["PUT"])
def api_update_message(message_id):
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    updated = update_message(message_id, content)
    if not updated:
        return jsonify({"error": "message not found"}), 404
    return jsonify({"ok": True})


def _session_payload(session_id):
    messages = get_messages(session_id)
    characters = sorted(get_session_characters(session_id), key=lambda c: c["id"])
    return {
        "session_id": session_id,
        "messages": [
            {"id": m["id"], "sender": m["sender"], "content": m["content"]} for m in messages
        ],
        "characters": [c["name"] for c in characters],
    }


@app.route("/api/session")
def api_session():
    return jsonify(_session_payload(get_or_create_session_id()))


@app.route("/api/session/<int:session_id>")
def api_session_by_id(session_id):
    """Loads a specific past conversation - used when switching to one from
    the Conversations list, instead of always resuming the latest."""
    return jsonify(_session_payload(session_id))


@app.route("/api/session/new", methods=["POST"])
def api_new_session():
    data = request.get_json(silent=True) or {}
    character_names = data.get("characters")
    name = (data.get("name") or "").strip() or "Chat Session"

    session_id = create_session(name)
    if character_names:
        set_session_characters(session_id, character_names)

    return jsonify({"session_id": session_id})


@app.route("/api/sessions")
def api_sessions():
    """Lists every conversation, most recently created first - powers the
    Conversations list in the web UI (switch/rename/delete)."""
    sessions = sorted(get_all_sessions(), key=lambda s: s["id"], reverse=True)
    return jsonify([
        {
            "id": s["id"], "name": s["name"],
            "message_count": s["message_count"], "created_at": s["created_at"],
        }
        for s in sessions
    ])


@app.route("/api/sessions/<int:session_id>", methods=["PUT"])
def api_rename_session(session_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    renamed = rename_session(session_id, name)
    if not renamed:
        return jsonify({"error": "conversation not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    deleted = delete_session(session_id)
    if not deleted:
        return jsonify({"error": "conversation not found"}), 404

    # Tear down any in-memory state so a stray idle timer or subscriber list
    # doesn't linger for a conversation that no longer exists.
    _cancel_idle_check(session_id)
    with _lock:
        _session_queues.pop(session_id, None)
        _session_subscribers.pop(session_id, None)
        _workers_started.discard(session_id)

    return jsonify({"ok": True})


@app.route("/api/message", methods=["POST"])
def api_message():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    user_message = (data.get("message") or "").strip()

    if not session_id or not user_message:
        return jsonify({"error": "session_id and message are required"}), 400

    _ensure_worker(session_id)
    _cancel_idle_check(session_id)
    _get_queue(session_id).put(("user", user_message))

    return jsonify({"queued": True}), 202


@app.route("/api/stream/<int:session_id>")
def api_stream(session_id):
    """Server-sent events: each character reply for this session is pushed
    here as soon as it's generated, so the browser can render replies one by
    one instead of waiting for a whole round to finish."""
    def events():
        subscriber_queue = _subscribe(session_id)
        try:
            while True:
                try:
                    event = subscriber_queue.get(timeout=20)
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
        finally:
            _unsubscribe(session_id, subscriber_queue)

    return Response(stream_with_context(events()), mimetype="text/event-stream")


if __name__ == "__main__":
    ensure_ready()
    app.run(debug=True, port=5000, threaded=True)
