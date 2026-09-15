from database import init_db, create_session, add_message
from router import decide_speakers
from character_response import generate_character_reply

MAX_CHARACTER_TURNS_PER_MESSAGE = 6


def run_conversation_turn(session_id, user_message):
    """Lets characters react to the user, then to each other, for a few rounds
    before handing control back to the user."""
    add_message(session_id, "user", user_message)

    latest_message = user_message
    last_speaker = None
    turns_used = 0

    while turns_used < MAX_CHARACTER_TURNS_PER_MESSAGE:
        speakers = decide_speakers(session_id, latest_message, exclude=last_speaker)
        if not speakers:
            break

        for name in speakers:
            if turns_used >= MAX_CHARACTER_TURNS_PER_MESSAGE:
                break
            reply = generate_character_reply(session_id, name)
            print(f"{name}: {reply}")
            latest_message = reply
            last_speaker = name
            turns_used += 1


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

        try:
            run_conversation_turn(session_id, user_message)
        except (RuntimeError, ValueError) as e:
            print(f"(something went wrong generating a reply, try again: {e})")


if __name__ == "__main__":
    main()
