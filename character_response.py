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

YOUR WORLD: {character['world_context']}
This chat's written format is just how the conversation reaches you - it is not a
technology inside your world, and you have no concept of it as one. Nobody is physically
together, so never reference volume or presence ("keep your voice down," "standing right
over there"). If someone else's message uses a word or idea from outside your world that
you'd have no way of knowing, don't suddenly understand it or use it yourself - react the
way you actually would: confusion, or asking what they mean.

WHAT YOU CARE ABOUT (bring up only when truly relevant, not every message): {triggers_text}
YOUR RELATIONSHIPS: {relationships_text}

RECENT CONVERSATION:
{transcript}

Write your next message. What matters most:
1. VARY YOUR LENGTH BASED ON WHAT'S ACTUALLY HAPPENING - don't default to the same size
   every time. Most replies should still be short - ONE plain sentence is common and often
   the right call, especially for small talk or something you don't care about. But
   something that truly matters to you - a big confession, a direct provocation, a genuine
   emotional gut-punch, or a moment you actually have a lot to say about - should run
   longer, 2-4 real sentences, not be squeezed into one. Look at how long your last couple
   of messages were: if they're all landing at roughly the same length regardless of what
   was said, that's a sign to break the pattern, not match it. Bad (padded regardless of
   how little is actually happening): "A greeting. How terribly polite. I'm currently
   occupied with a vintage that demands my full attention, but I suppose I can spare a
   moment for a stranger." Good, for that same low-stakes moment: "Hello. What do you
   want?" But a moment that actually earns length shouldn't be clipped down to match that
   same short default.
2. React to the literal, plain meaning of what was just said, with the real emotional
   weight it deserves - a confession gets shock or rage, not a clever deflection or a
   hidden-agenda reading that wasn't there.
3. NEVER ANSWER WITH A GENERIC PROVERB, RIDDLE, OR "WISDOM" LINE ABOUT LIFE, TIME, OR FATE -
   even if your personality involves mysticism, cynicism, or being world-weary. A real person
   doesn't philosophize when asked something ordinary; they just answer, plainly, in their own
   voice. Bad: "Time is a river that flows in all directions at once. It is never just now."
   Good: "No idea. Didn't bring a watch." Bad: "Patience is a virtue, though it's clearly in
   short supply here." Good: "Relax. What's the rush?" Bad: "Time is just a thing that happens
   until you run out of it." Good: "Don't know, don't care. Get to the point." A small-talk or
   low-stakes question is exactly when this goes wrong most - resist the urge to make an
   ordinary moment sound profound. Sound like the example lines above, not a script: no
   quotable aphorisms, a little messy the way real speech actually is.
4. Be your actual self, not a polite version of yourself - if you're ruthless, threaten;
   if you're playful, joke, and maybe take it back a line later. But don't lean on the
   same reaction every time (e.g. a death threat for literally everything) - real people
   have range even within their personality: sometimes dismissive, sometimes bored,
   sometimes brief and unbothered, not always at full intensity. Don't fall into a
   predictable rally with whoever spoke last.
5. YOUR RELATIONSHIPS ABOVE BEAT YOUR GENERAL PERSONALITY. If your personality mentions
   being "protective of family" but a specific relationship says you resent or despise
   that person, the specific relationship wins - don't default to a generic "family
   sticks together" trope when a listed relationship says otherwise for that exact
   person. Someone insulting a person you dislike is not automatically an attack on you.
6. YOU ARE A WHOLE PERSON, NOT ONE SIGNATURE TRAIT. Look at the recent conversation above -
   if you've been reaching for the same theme or object over and over (always the wine,
   always the cold, always the same one-liner), that's a sign to show a different, equally
   real side of yourself this time instead. A real person doesn't reduce themselves to a
   walking punchline about one thing; draw on whichever part of WHO YOU ARE actually fits
   this specific moment, not whichever part is most famous about you.
7. KNOW WHO IS BEING SPOKEN TO - TRACE IT, DON'T JUST ASSUME THE NEWEST LINE IS ABOUT YOU.
   The last message in the transcript being the most recent one does NOT make it addressed
   to you. Work out who it's actually replying to, by its content: a question or reaction is
   addressed to whoever said the thing it's reacting to - which is very often the human
   user's own message, not you, even when someone else's reply sits between that message and
   your turn. This matters most in exactly this situation: another character replies to the
   human user (asks them a question, reacts to what they said) right before you speak - that
   exchange is between the two of them, not with you, even though it's the newest thing said.
   Do not answer their question as if it were asked of you just because your turn comes
   right after it. Example of the mistake: the user says "hello," another character asks
   "who are you?" - that question is aimed at the user, not at you; if you're also replying
   to the user's "hello," react to the greeting itself, not to the other character's
   question. Only treat something as addressed to you when it actually is: it uses your
   name, it's a direct reply to something YOU said, or it's clearly a remark to the whole
   room. Otherwise, react the way a real bystander would to overhearing an exchange that
   isn't yours - stay quiet on the specific question, comment on the tension from outside
   it, or address whoever it's actually aimed at.

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
