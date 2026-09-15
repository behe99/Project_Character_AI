import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-3.1-flash-lite"

# We never use tool/function calling, so disable automatic function calling
# to silence the SDK's AFC warning on every call.
GENERATE_CONFIG = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)


def call_model(prompt, retries=3, backoff_seconds=3):
    """Sends a prompt to the model, retrying on failure. Raises RuntimeError if all attempts fail."""
    response = None
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=GENERATE_CONFIG,
            )
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(backoff_seconds)

    if response is None:
        raise RuntimeError(f"{MODEL} failed after {retries} attempts.")

    return response.text.strip()
