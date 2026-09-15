import json
from database import get_all_characters, get_messages, add_message
from llm import call_model


def get_character(name):
    characters = get_all_characters()
    for c in characters:
        if c["name"] == name:
            return c
    return None


def build_transcript(messages, limit=15):
    """Takes the last N messages and formats them as readable dialogue."""
    recent = messages[-limit:]
    lines = [f"{m['sender']}: {m['content']}" for m in recent]
    return "\n".join(lines)


def generate_character_reply(session_id, character_name):
    character = get_character(character_name)
    if character is None:
        raise ValueError(f"Character '{character_name}' not found in database.")

    messages = get_messages(session_id)
    transcript = build_transcript(messages)
    relationships = json.loads(character["relationships"])
    triggers = json.loads(character["triggers"])

    relationships_text = "\n".join(
        f"- {name}: {feeling}" for name, feeling in relationships.items()
    ) or "No specific relationships recorded."
    triggers_text = ", ".join(triggers) or "nothing in particular"

    prompt = f"""You are {character['name']}, actually here in this group chat. This is a real,
live conversation - not a scene you are performing or narrating.

PERSONALITY:
{character['personality']}

HOW YOU TALK:
{character['speech_style']}

THINGS YOU CARE ABOUT: {triggers_text}
(Only bring these up if the conversation genuinely lands on them. Most of your replies
should NOT mention them at all - don't turn every message into a reference to wine, war,
family, or whatever your interests are.)

YOUR RELATIONSHIPS WITH OTHERS HERE:
{relationships_text}

RECENT CONVERSATION:
{transcript}

Write {character['name']}'s next message. Follow these rules:

1. REACT TO WHAT WAS LITERALLY JUST SAID. Respond to the actual content of the last
   message, not to the general topic, your own interests, or a "deeper meaning." If
   someone says "hello," say hello back (or something equally plain) - don't pivot to
   your backstory or obsessions.
2. TALK LIKE A REAL PERSON, NOT A SCRIPT. No proverbs, no "X is like Y" metaphors, no
   aphorisms about blood/crowns/duty/wine as a rhetorical flourish. Most lines should be
   plain, direct, and a little messy - the way people actually talk - not quotable.
3. LENGTH: default to ONE short, plain sentence, well under 15 words. Only go to 2-3
   sentences when something you truly care about comes up or you're directly provoked,
   and even then react like a person, not deliver a monologue.
4. Use the vocabulary and rhythm from HOW YOU TALK above, but vary your phrasing between
   messages - don't repeat the same word, joke, or reference every time you speak.

Do NOT include your name as a prefix (e.g. don't write "Tyrion: ..."), just write the message itself.
"""

    reply_text = call_model(prompt)

    # Save this character's reply into the transcript
    add_message(session_id, character["name"], reply_text)

    return reply_text


def generate_replies_for_speakers(session_id, speaker_names):
    """Generates replies sequentially so each character sees prior replies in the same turn."""
    replies = []
    for name in speaker_names:
        reply = generate_character_reply(session_id, name)
        replies.append((name, reply))
        print(f"{name}: {reply}")
    return replies


if __name__ == "__main__":
    from database import create_session, add_message as add_msg
    from router import decide_speakers

    session_id = create_session("Test Session 2")
    user_message = "I think power should always come with sacrifice."
    add_msg(session_id, "user", user_message)

    speakers = decide_speakers(session_id, user_message)
    print("Router decided these characters should respond:", speakers)
    print()

    generate_replies_for_speakers(session_id, speakers)
