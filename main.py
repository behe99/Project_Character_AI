from database import init_db, create_session, add_message
from router import decide_speakers
from character_response import generate_replies_for_speakers


def main():
    init_db()
    session_id = create_session("Chat Session")
    print("Character AI chatroom. Type 'quit' to exit.\n")

    while True:
        user_message = input("You: ").strip()
        if not user_message:
            continue
        if user_message.lower() in ("quit", "exit"):
            break

        add_message(session_id, "user", user_message)

        speakers = decide_speakers(session_id, user_message)
        if not speakers:
            continue

        generate_replies_for_speakers(session_id, speakers)


if __name__ == "__main__":
    main()
