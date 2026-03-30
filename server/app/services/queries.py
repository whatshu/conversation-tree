from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Branch, Node, Run, RunEvent, Workspace
from app.schemas.common import BranchRead, NodeRead, RunEventRead, RunTraceRead, TreeRead, WorkspaceRead


def serialize_workspace(workspace: Workspace) -> WorkspaceRead:
    return WorkspaceRead.model_validate(workspace, from_attributes=True)


def list_branches(db: Session, workspace_id: str) -> list[BranchRead]:
    branches = list(
        db.scalars(select(Branch).where(Branch.workspace_id == workspace_id).order_by(Branch.created_at.asc()))
    )
    return [BranchRead.model_validate(branch, from_attributes=True) for branch in branches]


def list_nodes(db: Session, workspace_id: str) -> list[NodeRead]:
    nodes = list(db.scalars(select(Node).where(Node.workspace_id == workspace_id).order_by(Node.created_at.asc())))
    items: list[NodeRead] = []
    for node in nodes:
        latest_run = db.scalars(select(Run).where(Run.node_id == node.id).order_by(Run.created_at.desc())).first()
        summary = latest_run.summary.summary_text if latest_run and latest_run.summary else None
        items.append(
            NodeRead(
                id=node.id,
                workspace_id=node.workspace_id,
                parent_node_id=node.parent_node_id,
                user_prompt=node.user_prompt,
                created_at=node.created_at,
                latest_run_id=latest_run.id if latest_run else None,
                latest_assistant_message=latest_run.assistant_message if latest_run else None,
                latest_summary=summary,
            )
        )
    return items


def build_tree(db: Session, workspace: Workspace) -> TreeRead:
    return TreeRead(
        workspace=serialize_workspace(workspace),
        branches=list_branches(db, workspace.id),
        nodes=list_nodes(db, workspace.id),
    )


def get_node(db: Session, node_id: str) -> NodeRead | None:
    node = db.get(Node, node_id)
    if node is None:
        return None
    latest_run = db.scalars(select(Run).where(Run.node_id == node.id).order_by(Run.created_at.desc())).first()
    summary = latest_run.summary.summary_text if latest_run and latest_run.summary else None
    return NodeRead(
        id=node.id,
        workspace_id=node.workspace_id,
        parent_node_id=node.parent_node_id,
        user_prompt=node.user_prompt,
        created_at=node.created_at,
        latest_run_id=latest_run.id if latest_run else None,
        latest_assistant_message=latest_run.assistant_message if latest_run else None,
        latest_summary=summary,
    )


def get_trace(db: Session, node_id: str) -> RunTraceRead | None:
    run = db.scalars(select(Run).where(Run.node_id == node_id).order_by(Run.created_at.desc())).first()
    if run is None:
        return None
    events = list(db.scalars(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.sequence.asc())))
    return RunTraceRead(
        run_id=run.id,
        node_id=run.node_id,
        branch_id=run.branch_id,
        provider_name=run.provider_name,
        model_name=run.model_name,
        assistant_message=run.assistant_message,
        summary=run.summary.summary_text if run.summary else None,
        events=[RunEventRead.model_validate(event, from_attributes=True) for event in events],
    )


def rename_branch(db: Session, branch_id: str, name: str) -> BranchRead | None:
    branch = db.get(Branch, branch_id)
    if branch is None:
        return None
    branch.name = name
    branch.auto_named = False
    db.commit()
    db.refresh(branch)
    return BranchRead.model_validate(branch, from_attributes=True)
