# Character AI Chatroom

A group chat where fictional characters (currently a Game of Thrones cast)
respond to a human user and to each other, powered by Gemini.

- `database.py` — SQLite persistence for characters, sessions, and messages.
- `router.py` — decides which character(s), if any, should respond to the latest message.
- `character_response.py` — generates an in-character reply for a chosen speaker.
- `llm.py` — shared Gemini client/model call with retry logic.
- `seed_characters.py` — seeds the database with the character roster.
- `create_character.py` — interactively add your own character.
- `main.py` — interactive terminal chat loop.
- `app.py` — Flask web UI, built on the same `run_conversation_turn()` as main.py.
- `history.py` — list and view past conversations.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in GEMINI_API_KEY
python seed_characters.py
```

## Run

```bash
python main.py
```

Type a message and press enter. In-chat commands:
- `quit` — exit
- `new` — start a fresh conversation without deleting any history
- `characters` — list who's currently in the roster

Running `main.py` again resumes your most recent conversation instead of
starting over.

## Web UI

```bash
python app.py
```

Opens a Flask server at http://127.0.0.1:5000 with a browser chat interface:
colored character names, a roster legend, and a "New Conversation" button.
Uses the same database and the same `run_conversation_turn()` logic as
`main.py` - conversations started in one are visible in the other (and in
`history.py`) since they all share `chatroom.db`.

## Viewing past conversations

```bash
python history.py          # list all conversations
python history.py 2        # show the full transcript of session 2
```

## Creating a character

```bash
python create_character.py
```

Walks you through personality, speech style, backstory, a few sample lines
in their voice, relationships, triggers, and how likely they are to jump
into a conversation. Running it again with an existing character's name
overwrites their details instead of duplicating them.

When answering "one per line, blank line to finish" prompts (sample lines,
relationships), don't add extra blank lines for readability - a blank line
always means "I'm done with this section."

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

No API key needed - `tests/conftest.py` sets a dummy one and every test
mocks `call_model` directly, so the suite never makes real API calls and
runs against a fresh temp database per test.
