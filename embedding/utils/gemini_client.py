"""
Gemini Client Wrapper
Provides async + sync text generation using Gemini (Google Generative AI).
"""

import google.generativeai as genai
from config.settings import get_settings

settings = get_settings()


class GeminiClient:
    def __init__(self, model_name: str = "gemini-pro"):
        # Configure Gemini with API key
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str) -> str:
        """Synchronous text generation."""
        response = self.model.generate_content(prompt)
        return response.text

    async def generate_async(self, prompt: str) -> str:
        """Async-compatible generation. Simply wraps sync call."""
        # If you want true async later, replace this with aiohttp or google async client.
        return self.generate(prompt)
