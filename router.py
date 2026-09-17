import json
from database import get_session_characters, get_messages
from llm import call_model


def build_character_summary(characters):
    """Creates a short profile of each character for the router to reason over."""
    summary = []
    for c in characters:
        triggers = json.loads(c["triggers"])
        summary.append(
            f"- {c['name']}: {c['personality'][:100]}... "
            f"Triggers: {', '.join(triggers)}. "
            f"Interrupt tendency: {c['interrupt_tendency']}. "
            f"Assertiveness: {c['assertiveness']}."
        )
    return "\n".join(summary)


def build_transcript(messages, limit=10):
    """Takes the last N messages and formats them as readable dialogue."""
    recent = messages[-limit:]
    lines = [f"{m['sender']}: {m['content']}" for m in recent]
    return "\n".join(lines)


def decide_speakers(session_id, latest_message, exclude=None):
    characters = get_session_characters(session_id)
    messages = get_messages(session_id)

    character_summary = build_character_summary(characters)
    transcript = build_transcript(messages)

    prompt = f"""You are the router for a group chat between fictional characters and a human user.

CHARACTERS AVAILABLE:
{character_summary}

RECENT CONVERSATION:
{transcript}

LATEST MESSAGE:
{latest_message}

Decide which character(s), if any, would naturally respond to the latest message, based on:
- Relevance to their triggers/interests
- Their interrupt_tendency and assertiveness (higher = more likely to jump in)
- Whether the message is directed at them specifically
- Natural conversation flow (don't have everyone respond to everything)

PRIORITIZE PERSONAL STAKES. If the message directly hits one character's specific trigger
hard - insulting their family, wishing death on someone they love, attacking their
reputation to their face - that character should almost always be one of the speakers,
even if others could also plausibly respond. A generic "who might have an opinion on this
topic" pick is wrong when one character has the strongest, most personal reason to react.

Be conservative. Real group chats have quiet moments - not every message gets a reply,
and most that do only get one. A plain greeting or small talk ("hi", "how's it going")
should usually get 0 responses, or at most 1 brief one. If the latest message is itself
a character's reply (not the human user's), only continue the exchange when there's a
real reason to - a direct challenge, a contradiction, something aimed at someone
specifically - not just because the topic is still technically on the table. Most
back-and-forths should end after one or two exchanges, not run on.

DON'T DEFAULT TO THE SAME ONE OR TWO CHARACTERS OUT OF HABIT. Look at the recent
conversation - if the same pair has been trading lines for several messages in a row,
that's a sign to either let it end or bring in someone else with a genuine reason to
speak, not to keep it going between the same two people again.

RESPECT DIRECT ADDRESS. Work out who the latest message is actually aimed at - a direct
question or demand is usually addressed to whoever it's replying to (often the human
user), or to whoever is named explicitly ("Varys, answer me"). When the message is
clearly aimed at one specific person, everyone else is a bystander and should generally
stay silent, even if the topic touches their interests too. Only include a bystander in
this case if they have a strong, specific reason to interrupt - the remark also targets
them personally, or it's something they'd be compelled to react to - not just general
relevance. A demand directed at "Varys" should not produce other characters as speakers
unless something in the message also targets them specifically.

Choose AT MOST 2 characters. It's okay, and often correct, to choose 0.

Respond with ONLY valid JSON in this exact format, no other text:
{{"speakers": ["Character Name", "Character Name"]}}
"""

    raw = call_model(prompt)
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()

    try:
        result = json.loads(raw)
        speakers = result.get("speakers", [])
    except json.JSONDecodeError:
        print("Router returned invalid JSON:", raw)
        return []

    valid_names = {c["name"] for c in characters}
    dropped = [name for name in speakers if name not in valid_names]
    if dropped:
        print("Router picked unknown character(s), ignoring:", dropped)
    speakers = [name for name in speakers if name in valid_names]

    if exclude:
        speakers = [name for name in speakers if name != exclude]

    return speakers


if __name__ == "__main__":
    from database import create_session, add_message

    session_id = create_session("Test Session")
    add_message(session_id, "user", "I think power should always come with sacrifice.")

    speakers = decide_speakers(session_id, "I think power should always come with sacrifice.")
    print("Router decided these characters should respond:", speakers)
