import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

key = os.environ.get("GEMINI_API_KEY")
print("Key loaded:", key[:10] + "..." if key else "NOTHING LOADED")

client = genai.Client(api_key=key)

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="Say hello in one sentence."
)

print(response.text)