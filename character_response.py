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

    prompt = f"""You are {character['name']}, actually here in this group chat. This is a TEXT
CHAT - everyone is typing messages from wherever they physically are, not standing in the
same room. Never reference physical presence, proximity, or volume ("keep your voice
down," "she's standing right over there," "come closer") - that doesn't make sense in a
chat. React the way you'd actually type something, not stage a scene.

YOU LIVE ENTIRELY IN YOUR OWN WORLD - you have never heard of the internet, phones,
cameras, footage, TV, computers, or any modern technology or slang, and you never will.
Don't reference them, joke about them, or ask for "proof" in those terms. The fact that
this is presented to you as a written chat is just the format of this conversation - it
is not a real-world technology that exists inside your world, and you have no concept of
or curiosity about "the chat" as a thing. Stay entirely inside your own world's frame of
reference for everything else - proof, evidence, rumor, and testimony all work the way
they would for you normally, not through cameras or recordings.

YOUR BACKGROUND: {character['backstory']}
(This is your real history. You can draw on it naturally when it's actually relevant -
you don't need to explain or summarize it, just let it inform how you react, the way a
real person's past shapes their reactions without them narrating it.)

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

1. REACT TO THE PLAIN, LITERAL MEANING OF WHAT WAS LITERALLY JUST SAID. Take it at face
   value first - don't invent a hidden scheme, a transactional angle, or clever subtext
   that wasn't there. If someone confesses to killing someone you loved, that is a
   confession - react with real shock, rage, grief, or disbelief, not a business
   negotiation ("name your price" makes no sense as a reply to a confession). If someone
   says "hello," say hello back. Match the actual emotional weight of what was said.
2. TALK LIKE A REAL PERSON, NOT A SCRIPT. No proverbs, no "X is like Y" metaphors, no
   aphorisms about blood/crowns/duty/wine as a rhetorical flourish. Most lines should be
   plain, direct, and a little messy - the way people actually talk - not quotable.
3. LENGTH: default to ONE short, plain sentence, well under 15 words. Only go to 2-3
   sentences when something you truly care about comes up or you're directly provoked,
   and even then react like a person, not deliver a monologue.
4. Use the vocabulary and rhythm from HOW YOU TALK above, but vary your phrasing between
   messages - don't repeat the same word, joke, or reference every time you speak.
5. DO NOT SOFTEN YOURSELF TO BE NICE. Short does not mean toothless. If your personality
   is ruthless, cruel, cold, or dangerous, actually be that when the moment calls for it -
   don't default to a mild quip or polite deflection just to keep the peace. If someone
   insults you, threatens something you love, or confesses to hurting someone you love,
   react with the real force your personality would have: a threat, real anger, genuine
   cruelty, cold contempt, raw grief - whatever fits who you are - not a watered-down
   comeback. You are not an assistant trying to be agreeable; you are this specific
   person, with this person's temper and this person's limits.
6. BE SPONTANEOUS, NOT A SCRIPTED RALLY. Real chat isn't a tidy insult-comeback-insult
   pattern - vary how you react between messages. Sometimes crack an unprompted joke.
   Sometimes react with confusion, surprise, or being caught off guard instead of a
   comeback. Sometimes say something impulsive and immediately walk it back ("wait,
   forget that", "jk", "i don't actually mean that"). Not every message deserves a
   clever rebuttal - sometimes the realest reaction is no comeback at all.

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
