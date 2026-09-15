import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
config = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)

candidates = [
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash",
    "gemini-3.0-flash",
    "gemini-3.0-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

for name in candidates:
    start = time.time()
    try:
        resp = client.models.generate_content(model=name, contents="Say OK.", config=config)
        elapsed = time.time() - start
        print(f"{name}: OK ({elapsed:.2f}s) -> {resp.text.strip()[:40]!r}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"{name}: FAILED ({elapsed:.2f}s) -> {e}")
