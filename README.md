# Character AI Chatroom

A group chat where fictional characters (currently a Game of Thrones cast)
respond to a human user and to each other, powered by Groq.

- `database.py` — SQLite persistence for characters, sessions, and messages.
- `router.py` — decides which character(s), if any, should respond to the latest message.
- `character_response.py` — generates an in-character reply for a chosen speaker.
- `llm.py` — shared Groq client/model call with retry logic.
- `seed_characters.py` — seeds the database with the character roster.
- `main.py` — interactive chat loop.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in GROQ_API_KEY (get one free at https://console.groq.com)
python seed_characters.py
```

## Run

```bash
python main.py
```

Type a message and press enter. Type `quit` to exit.
