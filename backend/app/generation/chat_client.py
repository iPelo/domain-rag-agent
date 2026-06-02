"""Small chat-completion client used by the generation service."""

from __future__ import annotations

from typing import Any, Protocol

import httpx

from app.config import Settings


class ModelConfigurationError(RuntimeError):
    """Raised when generation is requested without usable model configuration."""


class ModelRequestError(RuntimeError):
    """Raised when the configured model provider rejects or fails a request."""


class ChatClient(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return one generated answer."""


class HostedChatClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelRequestError(f"Model request failed: {exc}") from exc

        content = _first_message_content(response.json())
        if not content:
            raise ModelRequestError("Model response did not include answer text.")
        return content.strip()


def build_chat_client(settings: Settings) -> ChatClient:
    provider = settings.model_provider.casefold()
    if provider != "hosted":
        raise ModelConfigurationError(f"Unsupported model provider: {settings.model_provider}")
    if not settings.model_api_key:
        raise ModelConfigurationError("MODEL_API_KEY is required for answer generation.")
    if not settings.model_name:
        raise ModelConfigurationError("MODEL_NAME is required for answer generation.")
    if not settings.model_base_url:
        raise ModelConfigurationError("MODEL_BASE_URL is required for answer generation.")

    return HostedChatClient(
        api_key=settings.model_api_key,
        model=settings.model_name,
        base_url=settings.model_base_url,
        temperature=settings.model_temperature,
        max_tokens=settings.model_max_tokens,
        timeout_seconds=settings.model_timeout_seconds,
    )


def _first_message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""
