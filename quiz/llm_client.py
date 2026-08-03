import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash-lite",
    "claude": "claude-sonnet-4-6",
}

_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
}


class LLMClient:
    """Unified LLM client that delegates to Claude or Gemini based on provider."""

    PROVIDERS = list(_DEFAULT_MODELS.keys())
    _total_calls: int = 0

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        dry_run: bool = False,
    ):
        self._provider = provider.lower()
        if self._provider not in _DEFAULT_MODELS:
            raise ValueError(
                f"Unknown provider '{provider}'. Choose from: {self.PROVIDERS}"
            )

        self._model = model or _DEFAULT_MODELS[self._provider]
        self._dry_run = dry_run

        if dry_run:
            logger.info("LLMClient initialised in DRY RUN mode — no real API calls will be made")
            return

        resolved_key = api_key or os.environ.get(_ENV_KEYS[self._provider])

        if self._provider == "claude":
            import anthropic
            self._client = anthropic.Anthropic(api_key=resolved_key)

        elif self._provider == "gemini":
            from google import genai
            self._genai_client = genai.Client(api_key=resolved_key)

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def model(self) -> str:
        return self._model

    @classmethod
    def total_calls(cls) -> int:
        return cls._total_calls

    def complete(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send a single-turn prompt and return the response text."""
        if self._dry_run:
            logger.info(
                "DRY RUN | provider=%s | model=%s | prompt_words=%d — skipping real API call\n--- PROMPT ---\n%s\n--- END PROMPT ---",
                self._provider,
                self._model,
                len(prompt.split()),
                prompt,
            )
            return (
                '[{"question": "[DRY RUN] Placeholder — no API call was made.",'
                ' "choices": ["A. Option A", "B. Option B", "C. Option C", "D. Option D"],'
                ' "answer": "A"}]'
            )

        LLMClient._total_calls += 1
        logger.info(
            "API call #%d | provider=%s | model=%s | prompt_words=%d",
            LLMClient._total_calls,
            self._provider,
            self._model,
            len(prompt.split()),
        )

        result: str
        if self._provider == "claude":
            import anthropic
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text_block = next(b for b in message.content if isinstance(b, anthropic.types.TextBlock))
            result = text_block.text

        elif self._provider == "gemini":
            from google.genai.errors import ClientError
            max_retries = 4
            delay = 15.0
            response = None
            for attempt in range(max_retries):
                try:
                    response = self._genai_client.models.generate_content(
                        model=self._model, contents=prompt
                    )
                    break
                except ClientError as e:
                    if e.code == 429 and attempt < max_retries - 1:
                        logger.warning(
                            "Gemini rate limit hit (attempt %d/%d), retrying in %.0fs",
                            attempt + 1, max_retries, delay,
                        )
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
            assert response is not None
            if response.text is None:
                raise ValueError("Gemini returned an empty response")
            result = response.text

        else:
            raise RuntimeError(f"Unhandled provider: {self._provider}")

        logger.info(
            "API response #%d | provider=%s | response_words=%d",
            LLMClient._total_calls,
            self._provider,
            len(result.split()),
        )
        return result
