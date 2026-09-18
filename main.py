import random

from colorama import Fore, Style, init as colorama_init

from database import (
    init_db, create_session, get_last_session, add_message,
    get_all_characters, get_session_characters, set_session_characters, get_messages,
)
from router import decide_speakers, decide_idle_speaker
from character_response import generate_character_reply
from seed_characters import seed

MAX_CHARACTER_TURNS_PER_MESSAGE = 4

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


def run_conversation_turn_stream(session_id, user_message, on_speaker_picked=None):
    """Same logic as run_conversation_turn, but yields each (character_name,
    reply) tuple as soon as it's generated instead of collecting them all
    first - so a caller can display or broadcast replies one at a time as
    they come in, rather than waiting for the whole round to finish.

    on_speaker_picked, if given, is called with a character's name the
    moment the router picks them - before their line is actually generated,
    which is the slow part. Callers can use this to show "X is typing..."
    instead of a generic indicator, or a blank one, while that line is
    still being written."""
    add_message(session_id, "user", user_message)

    latest_message = user_message
    last_speaker = None
    turns_used = 0
    is_first_round = True

    while turns_used < MAX_CHARACTER_TURNS_PER_MESSAGE:
        speakers = decide_speakers(
            session_id, latest_message, exclude=last_speaker, turns_so_far=turns_used
        )

        if not speakers:
            if not is_first_round:
                break
            fallback_pool = [
                c["name"] for c in get_session_characters(session_id) if c["name"] != last_speaker
            ]
            speakers = [random.choice(fallback_pool)]

        for name in speakers:
            if turns_used >= MAX_CHARACTER_TURNS_PER_MESSAGE:
                break
            if on_speaker_picked:
                on_speaker_picked(name)
            reply = generate_character_reply(session_id, name)
            yield name, reply
            latest_message = reply
            last_speaker = name
            turns_used += 1

        is_first_round = False


def run_conversation_turn(session_id, user_message):
    """Lets characters react to the user, then to each other, for a few rounds
    before handing control back to the user. The user's own message always gets
    at least one reply; character-to-character chains can still end at 0.
    Returns the generated replies as a list of (character_name, reply) tuples,
    in the order they were generated - callers decide how to display them.
    Prefer run_conversation_turn_stream() directly if you can display replies
    as they arrive instead of waiting for the whole list."""
    return list(run_conversation_turn_stream(session_id, user_message))


def run_idle_turn_stream(session_id, on_speaker_picked=None):
    """Lets one character speak up unprompted after a conversation has gone
    quiet for a while, instead of characters only ever reacting to the user
    or each other. Most of the time nobody has anything to say, so this
    yields nothing at all - it only yields a single (name, reply) when
    decide_idle_speaker() picks someone. See run_conversation_turn_stream
    for what on_speaker_picked is for."""
    speaker = decide_idle_speaker(session_id)
    if speaker is None:
        return
    if on_speaker_picked:
        on_speaker_picked(speaker)
    reply = generate_character_reply(session_id, speaker)
    yield speaker, reply


SHOW_ORDER = [
    "Game of Thrones", "Vikings", "The Walking Dead", "La Casa de Papel",
    "Squid Game", "Breaking Bad", "Prison Break", "Friends", "The Simpsons",
    "The Office", "Stranger Things",
]


def group_by_show(characters):
    """Groups characters by their show, in SHOW_ORDER's order first, then
    any other shows alphabetically - so a long roster reads as sections
    instead of one flat list."""
    groups = {}
    for c in characters:
        groups.setdefault(c.get("show") or "Custom", []).append(c)

    def sort_key(show):
        return (SHOW_ORDER.index(show), show) if show in SHOW_ORDER else (len(SHOW_ORDER), show)

    return [(show, groups[show]) for show in sorted(groups, key=sort_key)]


def list_characters(color_map):
    characters = sorted(get_all_characters(), key=lambda c: c["id"])
    if not characters:
        print("No characters in the roster.")
        return
    for show, group in group_by_show(characters):
        print(f"-- {show} --")
        for c in group:
            color = color_map.get(c["name"], Fore.WHITE)
            snippet = c["personality"].split(".")[0].strip()
            print(f"{color}{c['name']}{Style.RESET_ALL} - {snippet}")


def list_session_characters(session_id, color_map):
    characters = get_session_characters(session_id)
    for c in characters:
        color = color_map.get(c["name"], Fore.WHITE)
        print(f"{color}{c['name']}{Style.RESET_ALL}")


def choose_characters_cli():
    """Lets the user pick a subset of characters for a new conversation.
    Pressing enter with no input, or nothing valid getting picked, means
    everyone - the same default a fresh session already has. Numbers keep
    counting up across show sections, and typing a show's name instead
    (e.g. "Vikings") picks that whole cast without reading every number."""
    characters = sorted(get_all_characters(), key=lambda c: c["id"])
    grouped = group_by_show(characters)

    print("Choose characters for this conversation - comma-separated numbers, "
          "a show name to pick that whole cast (e.g. \"Vikings\"), "
          "or press enter for everyone:")
    numbered = []
    for show, group in grouped:
        print(f"-- {show} --")
        for c in group:
            numbered.append(c)
            print(f"  {len(numbered)}. {c['name']}")

    raw = input("> ").strip()
    if not raw:
        return [c["name"] for c in characters]

    show_names = {show.lower(): group for show, group in grouped}
    if raw.lower() in show_names:
        return [c["name"] for c in show_names[raw.lower()]]

    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(numbered):
            selected.append(numbered[int(part) - 1]["name"])

    return selected or [c["name"] for c in characters]


def start_new_session_cli():
    session_id = create_session("Chat Session")
    selected = choose_characters_cli()
    set_session_characters(session_id, selected)
    print(f"Started a new conversation with {', '.join(selected)}.\n")
    return session_id


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
    print("Character AI chatroom. Commands: 'quit', 'new' (fresh conversation, "
          "choose the cast), 'characters' (full roster), 'roster' (who's in "
          "this conversation).\n")

    while True:
        user_message = input("You: ").strip()
        if not user_message:
            continue

        command = user_message.lower()
        if command in ("quit", "exit"):
            break
        if command == "new":
            session_id = start_new_session_cli()
            continue
        if command == "characters":
            list_characters(color_map)
            print()
            continue
        if command == "roster":
            list_session_characters(session_id, color_map)
            print()
            continue

        try:
            for name, reply in run_conversation_turn_stream(session_id, user_message):
                print_character_line(name, reply, color_map)
        except (RuntimeError, ValueError) as e:
            print(f"(something went wrong generating a reply, try again: {e})")


if __name__ == "__main__":
    main()
