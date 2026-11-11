import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

MODEL = "gemini-3.5-flash-lite"
MAX_ATTEMPTS = 3
RETRY_CODES = {429, 503}

load_dotenv()
_client = genai.Client()


def generate_text(prompt):
    """Prompt'u Gemini'ye gönderir, cevap metnini döndürür."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = _client.models.generate_content(model=MODEL, contents=prompt)
            return response.text
        except errors.APIError as e:
            if e.code in RETRY_CODES and attempt < MAX_ATTEMPTS:
                wait = 10 * attempt
                print(f"Geçici hata ({e.code}), {wait} sn bekleniyor...")
                time.sleep(wait)
            else:
                raise