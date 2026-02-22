from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def ask_ai(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt,
        )

        if hasattr(response, "text") and response.text:
            return response.text

        if response.candidates:
            parts = response.candidates[0].content.parts
            return "".join(part.text for part in parts if hasattr(part, "text"))

        return "AI returned an empty response."

    except Exception as e:
        return f"AI error: {str(e)}"