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


def decide_speakers(session_id, latest_message, exclude=None, turns_so_far=0):
    characters = get_session_characters(session_id)
    messages = get_messages(session_id)

    character_summary = build_character_summary(characters)
    transcript = build_transcript(messages)

    if turns_so_far == 0:
        turn_pressure = (
            "This is the FIRST reply to this message - the most natural point for someone "
            "to speak up, if anyone should at all."
        )
    else:
        turn_pressure = (
            f"{turns_so_far} character(s) have already replied to this same message in this "
            "round. The bar for continuing climbs with every turn that's already happened - "
            "most exchanges should have already ended by now. Only add another speaker for a "
            "genuinely strong, specific reason (a direct challenge, their name called out, an "
            "unanswered provocation aimed at them) - not because the topic could still support "
            "more back-and-forth. Ending here (0 speakers) should be the most common outcome "
            "at this point, not the exception."
        )

    prompt = f"""You are the router for a group chat between fictional characters and a human user.

CHARACTERS AVAILABLE:
{character_summary}

RECENT CONVERSATION:
{transcript}

LATEST MESSAGE:
{latest_message}

{turn_pressure}

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

VARY THE COUNT MESSAGE TO MESSAGE. Don't fall into a habit of always picking the same
number of speakers - some messages genuinely deserve 0, some 1, occasionally more. If your
last several picks all landed on the same count, that alone is a reason to reconsider
whether this one really needs the same.

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
unless something in the message also targets them specifically. This also applies when
you're picking a SECOND character to react to the human user's own message: if you're
about to add someone else on top of a speaker who's already answering the user directly,
make sure that second character has their own real reason to speak, not just because the
first one is already talking to the user.

THIS INCLUDES WHEN THE USER IS THE ONE REPLYING. If a character just asked the human user
something directly, and the user's next message is a short, direct reply or follow-up
question that doesn't name anyone else, that's still a one-on-one exchange with that
specific character - not an opening for someone else to answer instead or in addition, even
if the question could technically apply to them too. Example of the mistake: a character
asks the user "what brings you here?", the user replies "who are you?" - only the character
who asked should answer that, not some other character jumping in to introduce themselves.

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


def decide_idle_speaker(session_id):
    """Decides whether any character would naturally break a silence and say
    something unprompted, instead of only ever reacting to the latest
    message. Used when a conversation has gone quiet for a while - separate
    from decide_speakers, which always reasons about a specific new message."""
    characters = get_session_characters(session_id)
    messages = get_messages(session_id)
    if not characters or not messages:
        return None

    character_summary = build_character_summary(characters)
    transcript = build_transcript(messages)

    prompt = f"""You are the router for a group chat between fictional characters and a human user.

CHARACTERS AVAILABLE:
{character_summary}

RECENT CONVERSATION (nobody has said anything for a while - it's gone quiet):
{transcript}

Decide whether ONE character would naturally break this silence and say something
unprompted - a new thought, something tied to their own interests or backstory,
circling back to something unresolved earlier in the conversation, or just casual
small talk. Weigh their interrupt_tendency and assertiveness (higher = more likely
to speak up into silence) and whether they'd genuinely have something to say right
now, not just whether they theoretically could.

BE CONSERVATIVE. This should be rare - most silences should just stay silent, the
same way most real group chats don't have someone constantly restarting the
conversation. Only pick a character when it clearly fits who they are.

Respond with ONLY valid JSON in this exact format, no other text:
{{"speaker": "Character Name"}} or {{"speaker": null}} if nobody would.
"""

    raw = call_model(prompt)
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()

    try:
        result = json.loads(raw)
        speaker = result.get("speaker")
    except json.JSONDecodeError:
        print("Router returned invalid JSON for idle check:", raw)
        return None

    valid_names = {c["name"] for c in characters}
    if speaker not in valid_names:
        if speaker is not None:
            print("Router picked unknown character for idle check, ignoring:", speaker)
        return None

    return speaker


if __name__ == "__main__":
    from database import create_session, add_message

    session_id = create_session("Test Session")
    add_message(session_id, "user", "I think power should always come with sacrifice.")

    speakers = decide_speakers(session_id, "I think power should always come with sacrifice.")
    print("Router decided these characters should respond:", speakers)
