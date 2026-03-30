from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Branch, Node, Run, RunEvent, SummaryTask, SummaryTaskStatus
from app.schemas.chat import ChatRequest
from app.services.graph import ConversationGraph
from app.services.providers import build_provider, dump_json
from app.services.tool_registry import ToolRegistry
from app.services.workspaces import build_auto_branch_name, ensure_main_branch


@dataclass(slots=True)
class BranchResolution:
    branch: Branch | None
    auto_branch_needed: bool


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.provider = build_provider()
        self.graph = ConversationGraph(provider=self.provider, tool_registry=ToolRegistry())

    async def stream_chat(self, workspace_id: str, request: ChatRequest) -> AsyncGenerator[dict, None]:
        prompt = request.prompt.strip()
        if len(prompt) > self.settings.max_prompt_chars:
            yield {"event": "error", "data": {"message": "Prompt exceeds configured limit."}}
            return

        resolution = self._resolve_branch(workspace_id, request.parent_node_id, request.branch_name)
        parent_node_id = request.parent_node_id or (resolution.branch.head_node_id if resolution.branch else None)

        node = Node(workspace_id=workspace_id, parent_node_id=parent_node_id, user_prompt=prompt)
        self.db.add(node)
        self.db.flush()

        run = Run(
            workspace_id=workspace_id,
            node_id=node.id,
            branch_id=resolution.branch.id if resolution.branch else None,
            provider_name=self.provider.name,
            model_name=self.settings.openai_model,
        )
        self.db.add(run)
        self.db.flush()

        state = await self.graph.run(prompt)
        sequence = 0
        tool_name = state.get("tool_name")
        tool_output = state.get("tool_output")
        assistant_message = state.get("assistant_message", "")

        if tool_name and tool_output:
            sequence += 1
            self._record_event(run.id, sequence, "tool_call", {"name": tool_name, "input": prompt})
            yield {"event": "tool_call", "data": {"name": tool_name, "input": prompt}}
            sequence += 1
            self._record_event(run.id, sequence, "tool_result", {"name": tool_name, "output": tool_output})
            yield {"event": "tool_result", "data": {"name": tool_name, "output": tool_output}}

        for chunk in self._chunk_text(assistant_message, 24):
            sequence += 1
            self._record_event(run.id, sequence, "token", {"text": chunk})
            yield {"event": "token", "data": {"text": chunk}}
            await asyncio.sleep(0)

        sequence += 1
        self._record_event(run.id, sequence, "assistant_final", {"message": assistant_message})
        run.assistant_message = assistant_message

        branch = self._finalize_branch(workspace_id, parent_node_id, node.id, prompt, resolution)
        run.branch_id = branch.id if branch else None
        self._enqueue_summary(run.id)
        self.db.commit()

        yield {"event": "assistant_final", "data": {"message": assistant_message}}
        yield {"event": "node_saved", "data": {"node_id": node.id, "branch_id": branch.id if branch else None}}
        yield {"event": "summary_status", "data": {"status": "queued", "run_id": run.id}}

    def _resolve_branch(
        self, workspace_id: str, parent_node_id: str | None, branch_name: str | None
    ) -> BranchResolution:
        branch = None
        if branch_name:
            branch = self.db.scalars(
                select(Branch).where(Branch.workspace_id == workspace_id, Branch.name == branch_name)
            ).first()
        else:
            branch = self.db.scalars(
                select(Branch).where(Branch.workspace_id == workspace_id, Branch.name == "main")
            ).first()
        auto_branch_needed = bool(
            branch and parent_node_id and branch.head_node_id and parent_node_id != branch.head_node_id
        )
        return BranchResolution(branch=branch, auto_branch_needed=auto_branch_needed)

    def _finalize_branch(
        self,
        workspace_id: str,
        parent_node_id: str | None,
        node_id: str,
        prompt: str,
        resolution: BranchResolution,
    ) -> Branch | None:
        if resolution.branch is None:
            branch = ensure_main_branch(self.db, workspace_id, head_node_id=node_id)
            return branch
        if resolution.auto_branch_needed:
            branch = Branch(
                workspace_id=workspace_id,
                name=build_auto_branch_name(prompt),
                base_node_id=parent_node_id,
                head_node_id=node_id,
                auto_named=True,
            )
            self.db.add(branch)
            self.db.flush()
            return branch
        resolution.branch.head_node_id = node_id
        self.db.flush()
        return resolution.branch

    def _record_event(self, run_id: str, sequence: int, event_type: str, payload: dict) -> None:
        self.db.add(
            RunEvent(
                run_id=run_id,
                sequence=sequence,
                event_type=event_type,
                payload_json=dump_json(payload),
            )
        )
        self.db.flush()

    def _enqueue_summary(self, run_id: str) -> None:
        self.db.add(SummaryTask(run_id=run_id, status=SummaryTaskStatus.pending))
        self.db.flush()

    @staticmethod
    def _chunk_text(text: str, size: int) -> list[str]:
        if not text:
            return [""]
        return [text[i : i + size] for i in range(0, len(text), size)]
