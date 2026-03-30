from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.providers import BaseProvider
from app.services.tool_registry import ToolRegistry


class ConversationState(TypedDict, total=False):
    prompt: str
    tool_name: str | None
    tool_output: str | None
    assistant_message: str


class ConversationGraph:
    """Minimal LangGraph orchestration with an optional safe tool step."""

    def __init__(self, provider: BaseProvider, tool_registry: ToolRegistry) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        graph = StateGraph(ConversationState)
        graph.add_node("tool", self._tool_node)
        graph.add_node("assistant", self._assistant_node)
        graph.add_edge(START, "tool")
        graph.add_edge("tool", "assistant")
        graph.add_edge("assistant", END)
        self.compiled = graph.compile()

    async def run(self, prompt: str) -> ConversationState:
        return await self.compiled.ainvoke({"prompt": prompt})

    async def _tool_node(self, state: ConversationState) -> ConversationState:
        result = self.tool_registry.maybe_run(state["prompt"])
        if result is None:
            return {"tool_name": None, "tool_output": None}
        return {"tool_name": result.name, "tool_output": result.output_text}

    async def _assistant_node(self, state: ConversationState) -> ConversationState:
        response = await self.provider.complete(
            prompt=state["prompt"],
            tool_output=state.get("tool_output"),
        )
        return {"assistant_message": response.content}
