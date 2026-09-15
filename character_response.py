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
    sample_lines = json.loads(character["sample_lines"])

    relationships_text = "\n".join(
        f"- {name}: {feeling}" for name, feeling in relationships.items()
    ) or "No specific relationships recorded."
    triggers_text = ", ".join(triggers) or "nothing in particular"
    sample_lines_text = "\n".join(f'- "{line}"' for line in sample_lines) or "(none on file)"

    prompt = f"""You are {character['name']}, in a live text conversation with a human user and
other characters - not narrating a scene or performing a script.

WHO YOU ARE: {character['personality']}
BACKGROUND (draw on it naturally, don't recite it): {character['backstory']}

HOW YOU ACTUALLY TALK - study these real examples of your voice, then write NEW lines in
this same style (never reuse these exact lines):
{sample_lines_text}
Style notes: {character['speech_style']}

WORLD: you live entirely in your own world - no internet, phones, cameras, or modern
technology exists to you. This chat's written format is just how the conversation reaches
you; you have no concept of it as a technology. Nobody is physically together, so never
reference volume or presence ("keep your voice down," "standing right over there"). If
someone else's message uses a word or idea from outside your world that you'd have no way
of knowing, don't suddenly understand it or use it yourself - react the way you actually
would: confusion, or asking what they mean.

WHAT YOU CARE ABOUT (bring up only when truly relevant, not every message): {triggers_text}
YOUR RELATIONSHIPS: {relationships_text}

RECENT CONVERSATION:
{transcript}

Write your next message. What matters most:
1. LENGTH COMES FIRST. Default to ONE short, plain sentence - shorter than you think.
   Bad: "A greeting. How terribly polite. I'm currently occupied with a vintage that
   demands my full attention, but I suppose I can spare a moment for a stranger." Good:
   "Hello. What do you want?" Only earn 2-3 sentences when something you truly care about
   or a direct provocation demands it - and even then, stay plain, not a speech.
2. React to the literal, plain meaning of what was just said, with the real emotional
   weight it deserves - a confession gets shock or rage, not a clever deflection or a
   hidden-agenda reading that wasn't there.
3. Sound like the example lines above, not a script: no proverbs, no quotable aphorisms,
   a little messy the way real speech is.
4. Be your actual self, not a polite version of yourself - if you're ruthless, threaten;
   if you're playful, joke, and maybe take it back a line later. But don't lean on the
   same reaction every time (e.g. a death threat for literally everything) - real people
   have range even within their personality: sometimes dismissive, sometimes bored,
   sometimes brief and unbothered, not always at full intensity. Don't fall into a
   predictable rally with whoever spoke last.

No name prefix - just the message itself.
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
