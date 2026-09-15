import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "llama-3.3-70b-versatile"


def call_model(prompt, retries=3, backoff_seconds=3):
    """Sends a prompt to the model, retrying on failure. Raises RuntimeError if all attempts fail."""
    response = None
    for attempt in range(retries):
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            response = completion.choices[0].message.content
            break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(backoff_seconds)

    if response is None:
        raise RuntimeError(f"{MODEL} failed after {retries} attempts.")

    return response.strip()
