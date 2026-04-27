import os
from typing import Optional

_DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-6",
    "gemini": "gemini-2.0-flash",
}

_ENV_KEYS = {
    "claude": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


class LLMClient:
    """Unified LLM client that delegates to Claude or Gemini based on provider."""

    PROVIDERS = list(_DEFAULT_MODELS.keys())

    def __init__(
        self,
        provider: str = "claude",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._provider = provider.lower()
        if self._provider not in _DEFAULT_MODELS:
            raise ValueError(
                f"Unknown provider '{provider}'. Choose from: {self.PROVIDERS}"
            )

        self._model = model or _DEFAULT_MODELS[self._provider]
        resolved_key = api_key or os.environ.get(_ENV_KEYS[self._provider])

        if self._provider == "claude":
            import anthropic
            self._client = anthropic.Anthropic(api_key=resolved_key)

        elif self._provider == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=resolved_key)
            self._genai_model = genai.GenerativeModel(self._model)

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send a single-turn prompt and return the response text."""
        if self._provider == "claude":
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        elif self._provider == "gemini":
            response = self._genai_model.generate_content(prompt)
            return response.text
