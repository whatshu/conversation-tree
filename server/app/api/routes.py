from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.core.security import verify_bearer_token
from app.db.session import get_db
from app.schemas.chat import ChatRequest
from app.schemas.common import BranchUpdate, TreeRead, WorkspaceCreate, WorkspaceRead
from app.services.chat import ChatService
from app.services.queries import build_tree, get_node, get_trace, list_branches, rename_branch, serialize_workspace
from app.services.workspaces import create_workspace, get_workspace, list_workspaces


router = APIRouter(prefix="/v1", dependencies=[Depends(verify_bearer_token)])


@router.post("/workspaces", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace_route(payload: WorkspaceCreate, db: Session = Depends(get_db)) -> WorkspaceRead:
    workspace = create_workspace(db, payload.name, payload.description)
    return serialize_workspace(workspace)


@router.get("/workspaces", response_model=list[WorkspaceRead])
def list_workspaces_route(db: Session = Depends(get_db)) -> list[WorkspaceRead]:
    return [serialize_workspace(item) for item in list_workspaces(db)]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceRead)
def get_workspace_route(workspace_id: str, db: Session = Depends(get_db)) -> WorkspaceRead:
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return serialize_workspace(workspace)


@router.get("/workspaces/{workspace_id}/tree", response_model=TreeRead)
def get_tree_route(workspace_id: str, db: Session = Depends(get_db)) -> TreeRead:
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return build_tree(db, workspace)


@router.get("/workspaces/{workspace_id}/branches")
def list_branches_route(workspace_id: str, db: Session = Depends(get_db)):
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return list_branches(db, workspace_id)


@router.patch("/workspaces/{workspace_id}/branches/{branch_id}")
def rename_branch_route(
    workspace_id: str,
    branch_id: str,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
):
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    branch = rename_branch(db, branch_id, payload.name)
    if branch is None:
        raise HTTPException(status_code=404, detail="Branch not found.")
    return branch


@router.get("/workspaces/{workspace_id}/nodes/{node_id}")
def get_node_route(workspace_id: str, node_id: str, db: Session = Depends(get_db)):
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    node = get_node(db, node_id)
    if node is None or node.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Node not found.")
    return node


@router.get("/workspaces/{workspace_id}/nodes/{node_id}/trace")
def get_trace_route(workspace_id: str, node_id: str, db: Session = Depends(get_db)):
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    trace = get_trace(db, node_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found.")
    return trace


@router.post("/workspaces/{workspace_id}/messages/stream")
async def stream_chat_route(
    workspace_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
):
    workspace = get_workspace(db, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    service = ChatService(db)

    async def event_generator():
        async for envelope in service.stream_chat(workspace_id, payload):
            yield {"event": envelope["event"], "data": json.dumps(envelope["data"], ensure_ascii=False)}

    return EventSourceResponse(event_generator())
