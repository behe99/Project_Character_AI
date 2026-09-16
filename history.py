import sys

from database import init_db, get_all_sessions, get_messages
from main import build_color_map, print_character_line


def list_sessions():
    sessions = get_all_sessions()
    if not sessions:
        print("No conversations yet.")
        return
    for s in sessions:
        print(f"[{s['id']}] {s['name']} - {s['message_count']} messages - {s['created_at']}")
    print("\nRun 'python history.py <session_id>' to view one.")


def show_session(session_id, color_map):
    messages = get_messages(session_id)
    if not messages:
        print(f"Session {session_id} has no messages.")
        return
    for m in messages:
        if m["sender"] == "user":
            print(f"You: {m['content']}")
        else:
            print_character_line(m["sender"], m["content"], color_map)


def main():
    init_db()
    color_map = build_color_map()

    if len(sys.argv) > 1:
        try:
            session_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python history.py [session_id]")
            return
        show_session(session_id, color_map)
    else:
        list_sessions()


if __name__ == "__main__":
    main()
