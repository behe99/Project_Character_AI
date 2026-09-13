import os
import json
import time
from dotenv import load_dotenv
from google import genai
from database import get_all_characters, get_messages

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-3.1-flash-lite"


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


def decide_speakers(session_id, latest_message):
    characters = get_all_characters()
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

Choose AT MOST 2 characters. It's okay to choose 0 if nothing warrants a response.

Respond with ONLY valid JSON in this exact format, no other text:
{{"speakers": ["Character Name", "Character Name"]}}
"""

    response = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(3)

    if response is None:
        raise RuntimeError(f"{MODEL} failed after 3 attempts.")

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").replace("json", "", 1).strip()

    try:
        result = json.loads(raw)
        return result.get("speakers", [])
    except json.JSONDecodeError:
        print("Router returned invalid JSON:", raw)
        return []


if __name__ == "__main__":
    from database import create_session, add_message

    session_id = create_session("Test Session")
    add_message(session_id, "user", "I think power should always come with sacrifice.")

    speakers = decide_speakers(session_id, "I think power should always come with sacrifice.")
    print("Router decided these characters should respond:", speakers)