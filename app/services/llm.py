from app.config import get_settings


class LLMService:
    """Optional LLM enrichment. Core planning remains deterministic."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def summarize_plan(self, context: dict) -> str:
        if not self.is_enabled():
            return context["fallback"]

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            response = await client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are FitGen AI, a practical coach-engineer. "
                            "Use only the supplied metrics. Be concise and actionable."
                        ),
                    },
                    {"role": "user", "content": str(context)},
                ],
                temperature=0.2,
                max_tokens=180,
            )
            return response.choices[0].message.content or context["fallback"]
        except Exception:
            return context["fallback"]
