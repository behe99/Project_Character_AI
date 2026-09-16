import random

from colorama import Fore, Style, init as colorama_init

from database import (
    init_db, create_session, get_last_session, add_message,
    get_all_characters, get_messages,
)
from router import decide_speakers
from character_response import generate_character_reply
from seed_characters import seed

MAX_CHARACTER_TURNS_PER_MESSAGE = 3

COLOR_PALETTE = [
    Fore.CYAN, Fore.YELLOW, Fore.GREEN, Fore.MAGENTA,
    Fore.BLUE, Fore.RED, Fore.LIGHTCYAN_EX, Fore.LIGHTYELLOW_EX,
    Fore.LIGHTGREEN_EX, Fore.LIGHTMAGENTA_EX, Fore.LIGHTBLUE_EX, Fore.LIGHTRED_EX,
]


def build_color_map():
    """Assigns each character a stable color based on their fixed database id,
    so the same character always gets the same color across runs."""
    characters = sorted(get_all_characters(), key=lambda c: c["id"])
    return {
        c["name"]: COLOR_PALETTE[i % len(COLOR_PALETTE)]
        for i, c in enumerate(characters)
    }


def print_character_line(name, reply, color_map):
    color = color_map.get(name, Fore.WHITE)
    print(f"{color}{name}:{Style.RESET_ALL} {reply}")


def run_conversation_turn(session_id, user_message, color_map):
    """Lets characters react to the user, then to each other, for a few rounds
    before handing control back to the user. The user's own message always gets
    at least one reply; character-to-character chains can still end at 0."""
    add_message(session_id, "user", user_message)

    latest_message = user_message
    last_speaker = None
    turns_used = 0
    is_first_round = True

    while turns_used < MAX_CHARACTER_TURNS_PER_MESSAGE:
        speakers = decide_speakers(session_id, latest_message, exclude=last_speaker)

        if not speakers:
            if not is_first_round:
                break
            fallback_pool = [
                c["name"] for c in get_all_characters() if c["name"] != last_speaker
            ]
            speakers = [random.choice(fallback_pool)]

        for name in speakers:
            if turns_used >= MAX_CHARACTER_TURNS_PER_MESSAGE:
                break
            reply = generate_character_reply(session_id, name)
            print_character_line(name, reply, color_map)
            latest_message = reply
            last_speaker = name
            turns_used += 1

        is_first_round = False


def resume_or_create_session(color_map, recap_limit=6):
    last_session = get_last_session()
    if last_session is None:
        return create_session("Chat Session")

    messages = get_messages(last_session["id"])
    if not messages:
        return last_session["id"]

    print(f"Resuming previous conversation ({len(messages)} messages so far).\n")
    for m in messages[-recap_limit:]:
        if m["sender"] == "user":
            print(f"You: {m['content']}")
        else:
            print_character_line(m["sender"], m["content"], color_map)
    print()
    return last_session["id"]


def main():
    colorama_init()
    init_db()
    if not get_all_characters():
        print("No characters found in the database, seeding the roster...")
        seed()

    color_map = build_color_map()
    session_id = resume_or_create_session(color_map)
    print("Character AI chatroom. Type 'quit' to exit.\n")

    while True:
        user_message = input("You: ").strip()
        if not user_message:
            continue
        if user_message.lower() in ("quit", "exit"):
            break

        try:
            run_conversation_turn(session_id, user_message, color_map)
        except (RuntimeError, ValueError) as e:
            print(f"(something went wrong generating a reply, try again: {e})")


if __name__ == "__main__":
    main()
