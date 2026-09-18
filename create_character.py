from database import init_db, add_character, update_character, get_all_characters

VALID_LEVELS = ("low", "medium", "high")


def prompt(label, required=True):
    while True:
        value = input(f"{label}: ").strip()
        if value or not required:
            return value
        print("This is required, try again.")


def prompt_level(label, default="medium"):
    while True:
        value = input(f"{label} ({'/'.join(VALID_LEVELS)}, default {default}): ").strip().lower()
        if not value:
            return default
        if value in VALID_LEVELS:
            return value
        print(f"Please enter one of: {', '.join(VALID_LEVELS)}")


def prompt_list(label, example):
    print(f"{label} (one per line, blank line to finish. Example: {example})")
    items = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        items.append(line)
    return items


def prompt_relationships():
    print("Relationships to other characters (format 'Name: how they feel about them', "
          "blank line to finish)")
    relationships = {}
    while True:
        line = input("> ").strip()
        if not line:
            break
        if ":" not in line:
            print("Use the format 'Name: feeling', e.g. 'Jon Snow: trusts him completely'")
            continue
        name, feeling = line.split(":", 1)
        relationships[name.strip()] = feeling.strip()
    return relationships


def create_character():
    init_db()
    existing = get_all_characters()
    existing_names = {c["name"] for c in existing}
    existing_shows = sorted({c.get("show") or "Custom" for c in existing})

    print("Create a new character. Press Ctrl+C at any point to cancel.\n")

    name = prompt("Name")
    is_update = name in existing_names
    if is_update:
        print(f"'{name}' already exists - this will overwrite their details.\n")

    shows_hint = f" (existing: {', '.join(existing_shows)})" if existing_shows else ""
    show = prompt(
        f"Show/universe they're from{shows_hint} - reuse an existing name so they "
        "group together in the picker, or type a new one",
        required=False,
    ) or "Custom"

    avatar = prompt(
        "Avatar - a single emoji shown next to their name (e.g. \U0001F377 or \U0001F409). "
        "Leave blank to just use their first initial",
        required=False,
    )

    personality = prompt(
        "Personality - describe MULTIPLE distinct sides of them, not just their most "
        "famous trait (e.g. not just 'brilliant strategist', but also their humor, "
        "warmth, insecurities, what they're like in a quiet moment). A character "
        "reduced to one trait ends up repeating themselves constantly in chat."
    )
    speech_style = prompt(
        "Speech style (how they talk - and mention that they keep it SHORT, "
        "since that matters a lot for how they'll actually sound in chat)"
    )
    world_context = prompt(
        "Their world/setting (e.g. 'modern-day Earth, phones and the internet are "
        "normal' or 'medieval fantasy, no technology exists'). This matters: without "
        "it, they may default to assuming a fantasy setting or get confused by "
        "ordinary things from their own world."
    )
    backstory = prompt("Backstory (their real history - can be a few sentences)", required=False)

    print()
    sample_lines = prompt_list(
        "Sample lines - aim for 5-6 SHORT lines spanning different moods (a joke, "
        "warmth, irritation, a mundane reaction, their signature trait) - not all the "
        "same tone, or they'll come across one-dimensional",
        '"Didn\'t ask." or "Careful. I don\'t forget things like that."'
    )
    if not sample_lines:
        print("Warning: no sample lines means the model has nothing to anchor their voice to.")

    print()
    relationships = prompt_relationships()

    print()
    triggers_raw = prompt(
        "Triggers/interests, comma-separated (e.g. wine, politics, family)", required=False
    )
    triggers = [t.strip() for t in triggers_raw.split(",") if t.strip()]

    print()
    interrupt_tendency = prompt_level("Interrupt tendency (how likely to jump into a conversation)")
    assertiveness = prompt_level("Assertiveness (how forcefully they speak up)")

    character = dict(
        name=name,
        show=show,
        avatar=avatar,
        personality=personality,
        speech_style=speech_style,
        world_context=world_context,
        backstory=backstory,
        sample_lines=sample_lines,
        relationships=relationships,
        triggers=triggers,
        interrupt_tendency=interrupt_tendency,
        assertiveness=assertiveness,
    )

    if is_update:
        update_character(**character)
        print(f"\nUpdated {name}.")
    else:
        add_character(**character)
        print(f"\nAdded {name}. They'll show up next time you run main.py.")


if __name__ == "__main__":
    try:
        create_character()
    except KeyboardInterrupt:
        print("\nCancelled.")
