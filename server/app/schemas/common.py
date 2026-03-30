from datetime import datetime

from pydantic import BaseModel


class WorkspaceCreate(BaseModel):
    name: str
    description: str | None = None


class WorkspaceRead(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class BranchUpdate(BaseModel):
    name: str


class BranchRead(BaseModel):
    id: str
    workspace_id: str
    name: str
    base_node_id: str | None
    head_node_id: str | None
    auto_named: bool
    created_at: datetime
    updated_at: datetime


class NodeRead(BaseModel):
    id: str
    workspace_id: str
    parent_node_id: str | None
    user_prompt: str
    created_at: datetime
    latest_run_id: str | None = None
    latest_assistant_message: str | None = None
    latest_summary: str | None = None


class RunEventRead(BaseModel):
    id: str
    run_id: str
    sequence: int
    event_type: str
    payload_json: str
    created_at: datetime


class RunTraceRead(BaseModel):
    run_id: str
    node_id: str
    branch_id: str | None
    provider_name: str
    model_name: str
    assistant_message: str | None
    summary: str | None
    events: list[RunEventRead]


class TreeRead(BaseModel):
    workspace: WorkspaceRead
    branches: list[BranchRead]
    nodes: list[NodeRead]
