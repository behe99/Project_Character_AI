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

    prompt = f"""You are roleplaying as {character['name']} in a group chat.

PERSONALITY:
{character['personality']}

SPEECH STYLE:
{character['speech_style']}

THINGS YOU CARE ABOUT (you light up and get more talkative when these come up):
{triggers_text}

YOUR RELATIONSHIPS WITH OTHERS IN THIS CHAT:
{relationships_text}

RECENT CONVERSATION:
{transcript}

Write {character['name']}'s next message, staying fully in character.

LENGTH: Default to ONE short sentence, well under 15 words, like a real chat message.
Only go longer (2-3 sentences, still conversational, never a speech) when the latest
message touches something you care about (see above) or is aimed at you directly.
Small talk, greetings, and mundane remarks always get the short version. Most of your
replies should be short - reserve length for when it's actually earned.

VOCABULARY: Use the specific word choices, rhythm, and tone described in your SPEECH
STYLE above, not a generic "medieval fantasy" narrator voice. You should sound
recognizably like yourself and different from the other characters, the way you talk
in the show, not interchangeable with the others.

Never force your interests or backstory into a conversation that has nothing to do with
them. A genuine person doesn't launch into a speech about war because someone said hi.

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
