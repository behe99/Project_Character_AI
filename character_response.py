import os
import json
import time
from dotenv import load_dotenv
from google import genai
from database import get_all_characters, get_messages, add_message

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-3.1-flash-lite"


def get_character(name):
    characters = get_all_characters()
    for c in characters:
        if c["name"] == name:
            return c
    return None


def build_transcript(messages, limit=15):
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

    relationships_text = "\n".join(
        f"- {name}: {feeling}" for name, feeling in relationships.items()
    ) or "No specific relationships recorded."

    prompt = f"""You are roleplaying as {character['name']} in a group chat.

PERSONALITY:
{character['personality']}

SPEECH STYLE:
{character['speech_style']}

YOUR RELATIONSHIPS WITH OTHERS IN THIS CHAT:
{relationships_text}

RECENT CONVERSATION:
{transcript}

Write {character['name']}'s next message in the conversation. Stay fully in character.
Keep it to 1-4 sentences, like a real chat message, not a speech.
Do NOT include the character's name as a prefix (e.g. don't write "Tyrion: ..."), just write the message itself.
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

    reply_text = response.text.strip()
    add_message(session_id, character["name"], reply_text)
    return reply_text


def generate_replies_for_speakers(session_id, speaker_names):
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
