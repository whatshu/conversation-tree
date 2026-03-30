from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(slots=True)
class ToolCallResult:
    name: str
    input_text: str
    output_text: str


class ToolRegistry:
    """Safe built-in tools for local development and tests."""

    def maybe_run(self, prompt: str) -> ToolCallResult | None:
        normalized = prompt.strip().lower()
        if normalized.startswith("tool:time"):
            return ToolCallResult(
                name="time_lookup",
                input_text=prompt,
                output_text=datetime.now(timezone.utc).isoformat(),
            )
        if normalized.startswith("tool:echo"):
            payload = prompt.split(":", 2)[-1].strip() or "empty"
            return ToolCallResult(
                name="echo_context",
                input_text=prompt,
                output_text=f"echo:{payload}",
            )
        return None
