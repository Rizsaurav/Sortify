"""
Legacy Gemini Client Wrapper
Uses google-ai-generativelanguage (0.6.3) which works on Python 3.9
and supports .generate_content() exactly as before.
"""

import google.ai.generativelanguage as glm
from config.settings import get_settings

settings = get_settings()


class GeminiClient:
    def __init__(self, model_name="models/gemini-1.5-flash"):
        self.model_name = model_name

        self.client = glm.GenerativeServiceClient(
            client_options={"api_key": settings.google_api_key}
        )

        print(f"[GeminiClient] USING OLD GEMINI SDK with model={model_name}")

    def generate(self, prompt: str) -> str:
        try:
            req = glm.GenerateContentRequest(
                model=self.model_name,
                contents=[glm.Content(parts=[glm.Part(text=prompt)])]
            )

            res = self.client.generate_content(req)

            return res.candidates[0].content.parts[0].text

        except Exception as e:
            print(f"[GeminiClient ERROR]: {e}")
            return ""

    async def generate_async(self, prompt: str) -> str:
        return self.generate(prompt)

    async def summarize(self, query: str, context: str) -> str:
        prompt = f"""
You are a helpful assistant. Answer based ONLY on the context.

CONTEXT:
{context}

QUESTION:
{query}
"""
        return self.generate(prompt)
