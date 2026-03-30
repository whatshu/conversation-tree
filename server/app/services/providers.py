from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(slots=True)
class ProviderResponse:
    content: str


class BaseProvider:
    name = "base"

    async def complete(
        self,
        prompt: str,
        tool_output: str | None = None,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> ProviderResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    name = "mock"

    async def complete(
        self,
        prompt: str,
        tool_output: str | None = None,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> ProviderResponse:
        suffix = f" Tool result: {tool_output}." if tool_output else ""
        clean = re.sub(r"\s+", " ", prompt.strip())
        if system_prompt and "summary" in system_prompt.lower():
            compact = clean[:160]
            return ProviderResponse(content=f"Summary: {compact}")
        return ProviderResponse(content=f"Mock assistant reply to: {clean}.{suffix}".strip())


class OpenAICompatibleProvider(BaseProvider):
    name = "openai-compatible"

    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(
        self,
        prompt: str,
        tool_output: str | None = None,
        *,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> ProviderResponse:
        content = prompt if tool_output is None else f"{prompt}\n\nTool output:\n{tool_output}"
        payload = {
            "model": model or self.settings.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                    or "You are a helpful conversation tree assistant. Be concise and explicit.",
                },
                {"role": "user", "content": content},
            ],
        }
        async with httpx.AsyncClient(
            base_url=self.settings.openai_base_url.rstrip("/"),
            timeout=self.settings.request_timeout_seconds,
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
        ) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        message = data["choices"][0]["message"]["content"]
        if isinstance(message, list):
            text = "".join(part.get("text", "") for part in message)
        else:
            text = str(message)
        return ProviderResponse(content=text)


def build_provider() -> BaseProvider:
    settings = get_settings()
    if settings.enable_mock_provider or settings.openai_api_key == "change-me":
        return MockProvider()
    return OpenAICompatibleProvider()


async def generate_summary(
    provider: BaseProvider,
    *,
    user_prompt: str,
    assistant_message: str,
    tool_events: list[dict],
    model: str | None = None,
) -> str:
    event_lines = []
    for item in tool_events:
        event_type = item.get("event_type", "event")
        payload = item.get("payload", {})
        event_lines.append(f"- {event_type}: {payload}")

    summary_prompt = (
        "Summarize what happened between two conversation-tree nodes.\n"
        f"User prompt: {user_prompt}\n"
        f"Assistant final answer: {assistant_message}\n"
        "Tool activity:\n"
        f"{chr(10).join(event_lines) if event_lines else '- no tool usage'}"
    )
    response = await provider.complete(
        summary_prompt,
        system_prompt=(
            "You write short, concrete summaries for a conversation tree UI. "
            "Mention the assistant outcome and any important tool usage in one or two sentences."
        ),
        model=model,
    )
    return response.content.strip()


def dump_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
