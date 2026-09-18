# Character AI Chatroom

A group chat where fictional characters respond to a human user and to each
other, powered by Gemini. Ships with 45 characters across three shows: Game
of Thrones, Vikings, and The Walking Dead.

- `database.py` — SQLite persistence for characters, sessions, and messages.
- `router.py` — decides which character(s), if any, should respond to the latest message.
- `character_response.py` — generates an in-character reply for a chosen speaker.
- `llm.py` — shared Gemini client/model call with retry logic.
- `seed_characters.py` — seeds the database with the full character roster.
- `shows/` — one module per show (`got` characters live in `seed_characters.py`
  itself; `vikings.py` and `walking_dead.py` are separate modules combined in).
- `create_character.py` — interactively add your own character, from any show.
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
- `new` — start a fresh conversation; lets you pick which characters are in
  it. Characters are listed grouped by show, numbered continuously - type
  comma-separated numbers, type a show's name (e.g. `Vikings`) to grab that
  whole cast at once, or press enter for everyone
- `characters` — list every character in the database, grouped by show
- `roster` — list who's actually in the current conversation

Running `main.py` again resumes your most recent conversation instead of
starting over.

## Web UI

```bash
python app.py
```

Opens a Flask server at http://127.0.0.1:5000 with a browser chat interface:
colored character names, a roster legend for the current conversation, and
a "New Conversation" button. Uses the same database and the same
`run_conversation_turn_stream()` logic as `main.py` - conversations started
in one are visible in the other (and in `history.py`) since they all share
`chatroom.db`.

A few small usability touches: the send button is disabled until you've
typed something; Escape closes whichever modal is open; and scrolling up
to reread something doesn't get yanked back down by new replies arriving -
it only auto-scrolls if you were already at the bottom, or when it's your
own message being sent.

Replies stream in one at a time as each character finishes "typing," instead
of waiting for the whole round to land at once - and you're never locked out
of the input while that's happening. Send another message right away and
it's queued: characters finish replying to what's already in flight first,
then move on to your new message next, so an interruption never garbles a
reply that was already underway. Every message - including ones sent while
others were still being answered - stays in the same conversation history,
so characters can refer back to anything said earlier, interruption or not.

The typing indicator names who's about to reply ("Tyrion Lannister is
typing...") as soon as the router picks them, rather than a generic message
the whole time - it only falls back to the generic version for the brief gap
before anyone's been picked yet, or if the conversation is still deciding on
a follow-up after their line lands.

Characters can also speak up on their own. If a conversation you have open
goes quiet for a while (a minute or two, randomized so it doesn't feel
mechanical), one of them might occasionally say something unprompted - a new
thought, something tied to their own interests, or circling back to
something unresolved earlier - the same way a real group chat isn't always
waiting on you to say something first. This is deliberately rare (most
quiet moments should just stay quiet) and only happens while you actually
have the page open; closing the tab or switching conversations stops it.

Click "Manage Characters" to add a new character (same fields as
`create_character.py`, in a form) or remove an existing one, right from the
browser - no separate script needed.

Both "Manage Characters" and the "New Conversation" picker group characters
by show instead of one long list - so with 45+ characters you can jump
straight to "Vikings" or "The Walking Dead" instead of scanning everything.
Each group in the picker has its own "all"/"none" links alongside the
global "Select all"/"Select none". When adding a character, fill in the
"Show/universe" field with an existing show's name to group them with it,
or type a new one (leave it blank and they land under "Custom").

Every character gets a small emoji avatar - shown in the roster bar, the
character lists, the picker, and next to their name in chat - instead of
a plain colored dot, so it's easier to tell everyone apart at a glance. All
45 seeded characters have one already picked out; give a new character
their own via the "Avatar" field (a single emoji) when adding them, or
leave it blank and they'll just show their first initial instead.

Both modals also have a search box above the list - type a character's
name or a show's name (e.g. "vikings") to instantly narrow it down, useful
once you're adding your own characters on top of the seeded 45.

Click the "Light"/"Dark" button in the header to switch themes. Your choice
is remembered (via the browser's local storage) so it's still there next
time you open the page - it defaults to dark until you switch.

## Managing conversations

Click "Conversations" to see every conversation you've had, newest first -
each row shows its name, message count, and when it was created. Click a
name to switch to that conversation (the message feed and roster update in
place, no page reload needed); click the ✎ next to a name to rename it
in place; click "Delete" to remove a conversation and its messages for
good. New conversations default to "Chat Session," but the "New
Conversation" modal now has an optional name field so you can give one a
real name (like "Vikings mead hall") right when you create it, instead of
renaming it after the fact.

## Per-conversation casts

Each conversation can have its own subset of characters instead of always
including everyone - useful for a smaller, more focused scene, or once
you've added enough characters that not all of them make sense together.
Clicking "New Conversation" (web) or typing `new` (terminal) lets you pick
who's in that specific conversation; leaving everyone selected (or just
pressing enter in the terminal) keeps the old "everyone's in the room"
behavior. Conversations created before this feature, or where nobody
picked a subset, still include every character - nothing changes for them.

**With 45 characters spanning three different shows now, "everyone's in
the room" means Ragnar Lothbrok, Rick Grimes, and Tyrion Lannister are all
in the same conversation by default.** That can be fun as a novelty, but
for a focused, coherent conversation, pick just one show's cast when you
start a new conversation instead of leaving everyone checked.

## Viewing past conversations

```bash
python history.py          # list all conversations
python history.py 2        # show the full transcript of session 2
```

## Creating a character

```bash
python create_character.py
```

Walks you through their show/universe, an emoji avatar, personality, speech
style, world/setting, backstory, sample lines, relationships, triggers, and
how likely they are to jump into a conversation. Running it again with an
existing character's name overwrites their details instead of duplicating
them. Reuse an existing show's name (it lists what's already in the
database) to group a new character with that cast in the picker, or type a
new one for a show that isn't seeded yet.

When answering "one per line, blank line to finish" prompts (sample lines,
relationships), don't add extra blank lines for readability - a blank line
always means "I'm done with this section."

### Writing characters with real depth

Two fields matter more than they look for how alive a character feels:

- **World/setting** is not optional flavor text - it's what stops a modern
  character from being confused by phones, or a medieval character from
  casually mentioning the internet (a real bug this project hit before
  this field existed). Every character - GoT or otherwise - needs their
  own setting described, since the prompt no longer assumes any default.
- **Personality and sample lines should cover multiple sides of them**,
  not just their single most famous trait. A character described only as
  "brilliant strategist who drinks" or "broods about death" will reduce
  every message to that one theme - which is exactly what happened before
  this was fixed. Write personality as several distinct facets (their wit
  AND their warmth AND their insecurity), and write 5-6 sample lines
  spanning different moods (a joke, irritation, a mundane reaction,
  genuine vulnerability) instead of 2-3 lines that all sound the same.

This applies to characters from any show, not just the current Game of
Thrones cast - there's nothing GoT-specific left in the code.

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

No API key needed - `tests/conftest.py` sets a dummy one and every test
mocks `call_model` directly, so the suite never makes real API calls and
runs against a fresh temp database per test.
